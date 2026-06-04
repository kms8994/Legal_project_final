from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pipelines.common.env import ROOT, get_required_env, load_dotenv
from pipelines.common.articles import make_normalized_ref, normalize_law_name
from pipelines.common.law_api import (
    LawApiClient,
    exact_match_item,
    first_value,
    iter_dicts,
    normalize_space,
)


STATUTE_SCOPE_PATH = ROOT / "docs" / "StatuteScope.md"


@dataclass(frozen=True)
class StatuteRef:
    priority: str
    law_name: str
    article_no: int
    article_branch_no: int | None

    @property
    def normalized_ref(self) -> str:
        return make_normalized_ref(self.law_name, self.article_no, self.article_branch_no)

    @property
    def display_ref(self) -> str:
        branch = f"의{self.article_branch_no}" if self.article_branch_no else ""
        return f"{normalize_law_name(self.law_name)} 제{self.article_no}조{branch}"


@dataclass(frozen=True)
class LawRecord:
    law_code: str
    official_name: str
    short_name: str | None
    effective_date: date | None
    source_url: str | None


@dataclass(frozen=True)
class ArticleRecord:
    law_code: str
    article_code: str | None
    article_no: int
    article_branch_no: int | None
    paragraph_no: int | None
    subparagraph_no: int | None
    title: str | None
    body: str
    normalized_ref: str
    effective_date: date | None


@dataclass(frozen=True)
class CollectResult:
    laws: list[LawRecord]
    aliases: dict[str, list[str]]
    articles: list[ArticleRecord]
    failed_items: list[dict[str, Any]]


def parse_statute_refs(path: Path, priorities: set[str]) -> list[StatuteRef]:
    refs: list[StatuteRef] = []
    pattern = re.compile(r"^\|\s*(P\d+)\s*\|\s*(.+?)\s*\|")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        priority, raw_ref = match.groups()
        if priority not in priorities:
            continue
        parsed = parse_statute_ref(priority, raw_ref)
        if parsed:
            refs.append(parsed)
    return dedupe_refs(refs)


def parse_statute_ref(priority: str, raw_ref: str) -> StatuteRef | None:
    cleaned = normalize_space(raw_ref)
    match = re.match(r"(.+?)\s+제(\d+)조(?:의(\d+))?", cleaned)
    if not match:
        return None
    law_name, article_no, article_branch_no = match.groups()
    return StatuteRef(
        priority=priority,
        law_name=normalize_law_name(law_name),
        article_no=int(article_no),
        article_branch_no=int(article_branch_no) if article_branch_no else None,
    )


def dedupe_refs(refs: list[StatuteRef]) -> list[StatuteRef]:
    seen: set[tuple[str, int, int | None]] = set()
    deduped: list[StatuteRef] = []
    for ref in refs:
        key = (ref.law_name, ref.article_no, ref.article_branch_no)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def collect_laws(client: LawApiClient, refs: list[StatuteRef]) -> CollectResult:
    laws: list[LawRecord] = []
    aliases: dict[str, list[str]] = {}
    articles: list[ArticleRecord] = []
    failed_items: list[dict[str, Any]] = []

    refs_by_law: dict[str, list[StatuteRef]] = {}
    for ref in refs:
        refs_by_law.setdefault(ref.law_name, []).append(ref)

    for law_name, law_refs in refs_by_law.items():
        try:
            law_search = client.request_json(
                "lawSearch.do",
                {
                    "target": "eflaw",
                    "query": law_name,
                    "display": 20,
                    "page": 1,
                    "nw": 3,
                },
            )
            law_item = exact_match_item(
                law_search,
                ["법령명한글", "법령명", "lawName", "법령명_한글"],
                law_name,
            )
            if not law_item:
                failed_items.append({"law_name": law_name, "error": "exact_match_not_found"})
                continue

            law_id = str(first_value(law_item, ["법령ID", "lawId", "ID"]) or "")
            mst = str(first_value(law_item, ["법령일련번호", "MST", "mst"]) or "")
            detail_key = law_id or mst
            if not detail_key:
                failed_items.append({"law_name": law_name, "error": "detail_id_not_found"})
                continue

            law_detail = client.request_json(
                "lawService.do",
                {
                    "target": "eflaw",
                    "ID": detail_key,
                },
            )

            law_record = build_law_record(law_name, law_item, law_detail)
            laws.append(law_record)
            aliases[law_record.law_code] = build_aliases(law_record)

            for ref in law_refs:
                article = find_article(law_detail, ref, law_record)
                if article:
                    articles.append(article)
                else:
                    failed_items.append(
                        {
                            "law_name": ref.law_name,
                            "article": ref.display_ref,
                            "error": "article_not_found",
                        }
                    )
        except Exception as exc:  # noqa: BLE001 - pipeline records all failures.
            failed_items.append({"law_name": law_name, "error": str(exc)})

    return CollectResult(laws=laws, aliases=aliases, articles=articles, failed_items=failed_items)


def build_law_record(law_name: str, law_item: dict[str, Any], law_detail: Any) -> LawRecord:
    detail_info = exact_match_item(
        law_detail,
        ["법령명한글", "법령명", "lawName", "법령명_한글"],
        law_name,
    )
    source = detail_info or law_item
    law_code = str(first_value(source, ["법령ID", "lawId", "ID", "법령일련번호", "MST"]) or law_name)
    official_name = str(first_value(source, ["법령명한글", "법령명", "lawName", "법령명_한글"]) or law_name)
    short_name = optional_str(first_value(source, ["법령약칭명", "약칭", "shortName"]))
    effective_date = parse_yyyymmdd(first_value(source, ["시행일자", "시행일", "effectiveDate"]))
    source_url = optional_str(first_value(source, ["법령상세링크", "상세링크", "link"]))
    return LawRecord(
        law_code=law_code,
        official_name=official_name,
        short_name=short_name,
        effective_date=effective_date,
        source_url=source_url,
    )


def build_aliases(law: LawRecord) -> list[str]:
    values = [
        law.official_name,
        law.short_name,
        law.official_name.replace(" ", ""),
    ]
    manual = {
        "자동차손해배상 보장법": ["자배법", "자동차손배법"],
    }
    values.extend(manual.get(law.official_name, []))
    return sorted({value for value in values if value})


def find_article(law_detail: Any, ref: StatuteRef, law: LawRecord) -> ArticleRecord | None:
    candidates: list[tuple[int, ArticleRecord]] = []
    for item in iter_dicts(law_detail):
        article_no = parse_optional_int(first_value(item, ["조문번호", "조문번호문자열", "articleNo"]))
        if article_no != ref.article_no:
            continue

        branch = parse_optional_int(first_value(item, ["조문가지번호", "articleBranchNo"]))
        if (branch or None) != ref.article_branch_no:
            continue

        body = build_article_body(item)
        if not body:
            continue

        paragraph_no = parse_optional_int(first_value(item, ["항번호", "paragraphNo"]))
        subparagraph_no = parse_optional_int(first_value(item, ["호번호", "subparagraphNo"]))
        title = optional_str(first_value(item, ["조문제목", "조문제목문자열", "title"]))
        article_code = optional_str(first_value(item, ["조문키", "조문ID", "articleKey"]))

        record = ArticleRecord(
            law_code=law.law_code,
            article_code=article_code,
            article_no=ref.article_no,
            article_branch_no=ref.article_branch_no,
            paragraph_no=paragraph_no,
            subparagraph_no=subparagraph_no,
            title=title,
            body=body,
            normalized_ref=ref.normalized_ref,
            effective_date=law.effective_date,
        )
        candidates.append((score_article_candidate(item, ref, body), record))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def score_article_candidate(item: dict[str, Any], ref: StatuteRef, body: str) -> int:
    score = min(len(body), 1000)
    if optional_str(first_value(item, ["조문여부"])) == "조문":
        score += 5000
    branch = f"의{ref.article_branch_no}" if ref.article_branch_no else ""
    if body.startswith(f"제{ref.article_no}조{branch}"):
        score += 2000
    if first_value(item, ["조문제목", "조문제목문자열", "title"]):
        score += 500
    return score


def build_article_body(item: dict[str, Any]) -> str:
    parts = [
        value_to_text(
            first_value(
                item,
                ["조문내용", "조문내용문자열", "조문", "articleContent", "내용"],
            )
        )
    ]
    for child in iter_dicts(first_value(item, ["항", "호", "목"]) or []):
        child_text = first_value(child, ["항내용", "호내용", "목내용", "paragraphContent"])
        if child_text:
            parts.append(value_to_text(child_text))
    return normalize_space(strip_html(" ".join(part for part in parts if part)))


def upsert_result(database_url: str, result: CollectResult, params: dict[str, Any]) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                insert into pipeline_runs (
                  stage, status, source, params, finished_at,
                  input_count, success_count, failed_count, error_summary
                )
                values (
                  'collect_laws', %s, 'law.go.kr', %s, now(),
                  %s, %s, %s, %s
                )
                returning id
                """,
                (
                    "succeeded" if not result.failed_items else "partial_failed",
                    Jsonb(params),
                    len(result.laws) + len(result.articles),
                    len(result.laws) + len(result.articles),
                    len(result.failed_items),
                    json.dumps(result.failed_items, ensure_ascii=False) if result.failed_items else None,
                ),
            )

            for law in result.laws:
                cursor.execute(
                    """
                    insert into laws (
                      law_code, official_name, short_name, effective_date, source_url
                    )
                    values (%s, %s, %s, %s, %s)
                    on conflict (law_code, effective_date) do update set
                      official_name = excluded.official_name,
                      short_name = excluded.short_name,
                      source_url = excluded.source_url,
                      updated_at = now()
                    """,
                    (
                        law.law_code,
                        law.official_name,
                        law.short_name,
                        law.effective_date,
                        law.source_url,
                    ),
                )

                for alias in result.aliases.get(law.law_code, []):
                    cursor.execute(
                        """
                        insert into law_aliases (law_id, alias)
                        select id, %s
                        from laws
                        where law_code = %s
                          and coalesce(effective_date, date '1900-01-01') =
                              coalesce(%s, date '1900-01-01')
                        on conflict (law_id, alias) do nothing
                        """,
                        (alias, law.law_code, law.effective_date),
                    )

            for article in result.articles:
                cursor.execute(
                    """
                    insert into articles (
                      law_id, article_code, article_no, article_branch_no,
                      paragraph_no, subparagraph_no, title, body,
                      normalized_ref, effective_date
                    )
                    select
                      laws.id, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    from laws
                    where laws.law_code = %s
                      and coalesce(laws.effective_date, date '1900-01-01') =
                          coalesce(%s, date '1900-01-01')
                    on conflict (
                      law_id,
                      article_no,
                      (coalesce(article_branch_no, 0)),
                      (coalesce(paragraph_no, 0)),
                      (coalesce(subparagraph_no, 0)),
                      (coalesce(effective_date, date '1900-01-01'))
                    ) do update set
                      article_code = excluded.article_code,
                      title = excluded.title,
                      body = excluded.body,
                      normalized_ref = excluded.normalized_ref,
                      updated_at = now()
                    """,
                    (
                        article.article_code,
                        article.article_no,
                        article.article_branch_no,
                        article.paragraph_no,
                        article.subparagraph_no,
                        article.title,
                        article.body,
                        article.normalized_ref,
                        article.effective_date,
                        article.law_code,
                        article.effective_date,
                    ),
                )
        conn.commit()

    return {
        "laws_upserted": len(result.laws),
        "aliases_upserted": sum(len(items) for items in result.aliases.values()),
        "articles_upserted": len(result.articles),
        "failed_items": len(result.failed_items),
    }


def result_to_json(result: CollectResult) -> str:
    return json.dumps(
        {
            "laws": [record_to_json(law) for law in result.laws],
            "aliases": result.aliases,
            "articles": [record_to_json(article) for article in result.articles],
            "failed_items": result.failed_items,
        },
        ensure_ascii=False,
        indent=2,
    )


def record_to_json(value: Any) -> dict[str, Any]:
    data = asdict(value)
    for key, item in data.items():
        if isinstance(item, date):
            data[key] = item.isoformat()
    return data


def parse_priority(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


def parse_yyyymmdd(value: Any) -> date | None:
    if not value:
        return None
    text = re.sub(r"\D", "", str(value))
    if len(text) != 8:
        return None
    return datetime.strptime(text, "%Y%m%d").date()


def parse_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return normalize_space(str(value))


def value_to_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(value_to_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(value_to_text(item) for item in value.values())
    return str(value)


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    priorities = parse_priority(args.priority)
    refs = parse_statute_refs(STATUTE_SCOPE_PATH, priorities)
    if not refs:
        print(f"No statute refs found for priority={args.priority}", file=sys.stderr)
        return 2

    oc = get_required_env("LAW_API_OC", "LAW_API_KEY")
    client = LawApiClient(
        oc=oc,
        base_url=os.getenv("LAW_API_BASE_URL", "https://www.law.go.kr/DRF"),
        output_type=os.getenv("LAW_API_OUTPUT_TYPE", "JSON"),
        timeout=args.timeout,
        pause_seconds=args.pause_seconds,
    )

    result = collect_laws(client, refs)
    if args.dry_run:
        print(result_to_json(result))
        return 1 if result.failed_items else 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = upsert_result(
        database_url,
        result,
        {
            "scope": args.scope,
            "priority": sorted(priorities),
            "refs": [ref.display_ref for ref in refs],
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if result.failed_items else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect law and article rows for CaseLens.")
    parser.add_argument("--scope", default="damages", help="Collection scope label.")
    parser.add_argument("--priority", default="P0", help="Comma-separated priorities, e.g. P0 or P0,P1.")
    parser.add_argument("--dry-run", action="store_true", help="Print mapped rows without DB upsert.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    parser.add_argument("--pause-seconds", type=float, default=0.15, help="Pause between API calls.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
