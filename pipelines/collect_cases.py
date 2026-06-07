from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from pipelines.collect_laws import STATUTE_SCOPE_PATH, parse_priority, parse_statute_refs
from pipelines.common.env import get_required_env, load_dotenv
from pipelines.common.law_api import LawApiClient, first_value, iter_dicts, normalize_space


@dataclass(frozen=True)
class CaseListItem:
    external_id: str
    query: str
    case_no: str | None
    court_name: str | None
    court_level: str | None
    decision_date: date | None
    case_name: str | None
    case_type: str | None
    source_url: str | None


@dataclass(frozen=True)
class CaseRecord:
    external_id: str
    case_no: str
    court_name: str
    court_level: str | None
    decision_date: date | None
    case_name: str
    case_type: str | None
    legal_domain: str
    source_url: str | None
    raw_text: str
    raw_html: str
    source_hash: str


@dataclass(frozen=True)
class CollectCasesResult:
    queries_run: int
    list_rows_seen: int
    unique_case_ids: int
    details_fetched: int
    cases: list[CaseRecord]
    duplicates_skipped: int
    failed_items: list[dict[str, Any]]


def build_queries(priority: str, include_keywords: bool) -> list[str]:
    priorities = parse_priority(priority)
    refs = parse_statute_refs(STATUTE_SCOPE_PATH, priorities)
    queries = [ref.display_ref for ref in refs]
    if include_keywords:
        queries.extend(parse_keywords())
    return dedupe_strings(queries)


def parse_keywords() -> list[str]:
    keywords: list[str] = []
    in_section = False
    for line in STATUTE_SCOPE_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped == "## 5. 수집 키워드"
            continue
        if in_section and stripped.startswith("- "):
            keywords.append(stripped[2:].strip())
    return keywords


def collect_cases(
    client: LawApiClient,
    queries: list[str],
    limit: int,
    display: int,
    max_pages: int,
) -> CollectCasesResult:
    seen_ids: set[str] = set()
    list_items: list[CaseListItem] = []
    failed_items: list[dict[str, Any]] = []
    list_rows_seen = 0
    duplicates_skipped = 0
    queries_run = 0

    for query in queries:
        if len(seen_ids) >= limit:
            break
        for page in range(1, max_pages + 1):
            if len(seen_ids) >= limit:
                break
            queries_run += 1
            try:
                payload = client.request_json(
                    "lawSearch.do",
                    {
                        "target": "prec",
                        "query": query,
                        "search": 2,
                        "display": display,
                        "page": page,
                        "sort": "ddes",
                    },
                )
            except Exception as exc:  # noqa: BLE001 - pipeline records all failures.
                failed_items.append({"query": query, "page": page, "error": str(exc)})
                break

            items = extract_prec_items(payload)
            list_rows_seen += len(items)
            for item in items:
                parsed = parse_case_list_item(item, query)
                if not parsed:
                    failed_items.append({"query": query, "page": page, "error": "missing_case_serial"})
                    continue
                if parsed.external_id in seen_ids:
                    duplicates_skipped += 1
                    continue
                seen_ids.add(parsed.external_id)
                list_items.append(parsed)
                if len(seen_ids) >= limit:
                    break

            total_count = parse_optional_int(find_first_root_value(payload, ["totalCnt"])) or 0
            if not items or page * display >= total_count:
                break

    cases: list[CaseRecord] = []
    for item in list_items:
        try:
            detail = client.request_json(
                "lawService.do",
                {
                    "target": "prec",
                    "ID": item.external_id,
                },
            )
            cases.append(build_case_record(item, detail))
        except Exception as exc:  # noqa: BLE001 - pipeline records all failures.
            failed_items.append({"external_id": item.external_id, "error": str(exc)})

    return CollectCasesResult(
        queries_run=queries_run,
        list_rows_seen=list_rows_seen,
        unique_case_ids=len(seen_ids),
        details_fetched=len(cases),
        cases=cases,
        duplicates_skipped=duplicates_skipped,
        failed_items=failed_items,
    )


def extract_prec_items(payload: Any) -> list[dict[str, Any]]:
    for item in iter_dicts(payload):
        current = item.get("prec") or item.get("Prec") or item.get("판례")
        if isinstance(current, list):
            return [child for child in current if isinstance(child, dict)]
        if isinstance(current, dict):
            return [current]
    return []


def parse_case_list_item(item: dict[str, Any], query: str) -> CaseListItem | None:
    external_id = optional_str(first_value(item, ["판례일련번호", "판례정보일련번호", "ID"]))
    if not external_id:
        return None
    return CaseListItem(
        external_id=external_id,
        query=query,
        case_no=optional_str(first_value(item, ["사건번호"])),
        court_name=optional_str(first_value(item, ["법원명"])),
        court_level=optional_str(first_value(item, ["법원종류코드"])),
        decision_date=parse_date(first_value(item, ["선고일자"])),
        case_name=optional_str(first_value(item, ["사건명"])),
        case_type=optional_str(first_value(item, ["사건종류명"])),
        source_url=build_public_case_url(external_id),
    )


def build_case_record(item: CaseListItem, detail_payload: Any) -> CaseRecord:
    detail = find_service_dict(detail_payload)
    raw_text = normalize_space(strip_html(value_to_text(first_value(detail, ["판례내용"]))))
    raw_html = json.dumps(detail_payload, ensure_ascii=False, sort_keys=True)
    hash_source = raw_text or raw_html
    return CaseRecord(
        external_id=optional_str(first_value(detail, ["판례정보일련번호", "판례일련번호"])) or item.external_id,
        case_no=optional_str(first_value(detail, ["사건번호"])) or item.case_no or f"UNKNOWN-{item.external_id}",
        court_name=optional_str(first_value(detail, ["법원명"])) or item.court_name or "unknown",
        court_level=optional_str(first_value(detail, ["법원종류코드"])) or item.court_level,
        decision_date=parse_date(first_value(detail, ["선고일자"])) or item.decision_date,
        case_name=optional_str(first_value(detail, ["사건명"])) or item.case_name or "unknown",
        case_type=optional_str(first_value(detail, ["사건종류명"])) or item.case_type,
        legal_domain=_infer_legal_domain_from_case(
            optional_str(first_value(detail, ["사건명"])) or item.case_name or "",
            optional_str(first_value(detail, ["사건종류명"])) or item.case_type or "",
        ),
        source_url=item.source_url,
        raw_text=raw_text,
        raw_html=raw_html,
        source_hash=hashlib.sha256(normalize_space(hash_source).encode("utf-8")).hexdigest(),
    )


def upsert_result(database_url: str, result: CollectCasesResult, params: dict[str, Any]) -> dict[str, int]:
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
                  'collect_cases', %s, 'law.go.kr', %s, now(),
                  %s, %s, %s, %s
                )
                returning id
                """,
                (
                    "succeeded" if not result.failed_items else "partial_failed",
                    Jsonb(params),
                    result.list_rows_seen,
                    len(result.cases),
                    len(result.failed_items),
                    json.dumps(result.failed_items, ensure_ascii=False) if result.failed_items else None,
                ),
            )
            pipeline_run_id = cursor.fetchone()[0]

            for case in result.cases:
                cursor.execute(
                    """
                    select id
                    from cases
                    where external_id = %s
                       or (
                         case_no = %s
                         and decision_date is not distinct from %s
                         and court_name = %s
                       )
                       or source_hash = %s
                    limit 1
                    """,
                    (
                        case.external_id,
                        case.case_no,
                        case.decision_date,
                        case.court_name,
                        case.source_hash,
                    ),
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        """
                        update cases
                        set
                          external_id = %s,
                          case_no = %s,
                          court_name = %s,
                          court_level = %s,
                          decision_date = %s,
                          case_name = %s,
                          case_type = %s,
                          legal_domain = %s,
                          source_url = %s,
                          raw_text = %s,
                          raw_html = %s,
                          source_hash = %s,
                          pipeline_run_id = %s,
                          updated_at = now()
                        where id = %s
                        """,
                        (
                            case.external_id,
                            case.case_no,
                            case.court_name,
                            case.court_level,
                            case.decision_date,
                            case.case_name,
                            case.case_type,
                            case.legal_domain,
                            case.source_url,
                            case.raw_text,
                            case.raw_html,
                            case.source_hash,
                            pipeline_run_id,
                            existing[0],
                        ),
                    )
                    continue

                cursor.execute(
                    """
                    insert into cases (
                      external_id, case_no, court_name, court_level, decision_date,
                      case_name, case_type, legal_domain, source_url, raw_text,
                      raw_html, source_hash, pipeline_run_id
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (external_id) do update set
                      case_no = excluded.case_no,
                      court_name = excluded.court_name,
                      court_level = excluded.court_level,
                      decision_date = excluded.decision_date,
                      case_name = excluded.case_name,
                      case_type = excluded.case_type,
                      legal_domain = excluded.legal_domain,
                      source_url = excluded.source_url,
                      raw_text = excluded.raw_text,
                      raw_html = excluded.raw_html,
                      source_hash = excluded.source_hash,
                      pipeline_run_id = excluded.pipeline_run_id,
                      updated_at = now()
                    """,
                    (
                        case.external_id,
                        case.case_no,
                        case.court_name,
                        case.court_level,
                        case.decision_date,
                        case.case_name,
                        case.case_type,
                        case.legal_domain,
                        case.source_url,
                        case.raw_text,
                        case.raw_html,
                        case.source_hash,
                        pipeline_run_id,
                    ),
                )
        conn.commit()

    return {
        "queries_run": result.queries_run,
        "list_rows_seen": result.list_rows_seen,
        "unique_case_ids": result.unique_case_ids,
        "details_fetched": result.details_fetched,
        "cases_upserted": len(result.cases),
        "duplicates_skipped": result.duplicates_skipped,
        "failed_items": len(result.failed_items),
    }


def find_service_dict(payload: Any) -> dict[str, Any]:
    for item in iter_dicts(payload):
        if "PrecService" in item and isinstance(item["PrecService"], dict):
            return item["PrecService"]
    if isinstance(payload, dict):
        return payload
    return {}


def find_first_root_value(payload: Any, keys: list[str]) -> Any:
    for item in iter_dicts(payload):
        value = first_value(item, keys)
        if value not in (None, ""):
            return value
    return None


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return datetime.strptime(digits, "%Y%m%d").date()
    return None


def parse_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return normalize_space(str(value))


def build_public_case_url(external_id: str) -> str:
    return f"https://www.law.go.kr/판례/{external_id}"


def strip_html(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    return re.sub(r"<[^>]+>", " ", text)


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


def _infer_legal_domain_from_case(case_name: str, case_type: str) -> str:
    combined = f"{case_name} {case_type}".lower()
    if any(k in combined for k in ["형사", "피고인", "공소", "살인", "상해", "절도", "사기", "횡령", "강도", "강간", "음주운전"]):
        return "형사"
    if any(k in combined for k in ["손해배상", "불법행위", "구상금", "위자료"]):
        return "손해배상"
    return "민사"


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def result_to_json(result: CollectCasesResult) -> str:
    data = asdict(result)
    data["cases"] = [record_to_json(case) for case in result.cases]
    return json.dumps(data, ensure_ascii=False, indent=2)


def record_to_json(value: CaseRecord) -> dict[str, Any]:
    data = asdict(value)
    if value.decision_date:
        data["decision_date"] = value.decision_date.isoformat()
    data["raw_html"] = f"{len(value.raw_html)} bytes"
    data["raw_text"] = value.raw_text[:500]
    return data


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    queries = build_queries(args.priority, args.include_keywords)
    if args.query:
        queries = [args.query]
    if not queries:
        print("No collection queries found.", file=sys.stderr)
        return 2

    oc = get_required_env("LAW_API_OC", "LAW_API_KEY")
    client = LawApiClient(
        oc=oc,
        base_url=os.getenv("LAW_API_BASE_URL", "https://www.law.go.kr/DRF"),
        output_type=os.getenv("LAW_API_OUTPUT_TYPE", "JSON"),
        timeout=args.timeout,
        pause_seconds=args.pause_seconds,
    )

    result = collect_cases(
        client=client,
        queries=queries,
        limit=args.limit,
        display=args.display,
        max_pages=args.max_pages,
    )
    if args.dry_run:
        print(result_to_json(result))
        return 1 if result.failed_items else 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = upsert_result(
        database_url,
        result,
        {
            "scope": args.scope,
            "priority": args.priority,
            "include_keywords": args.include_keywords,
            "limit": args.limit,
            "display": args.display,
            "max_pages": args.max_pages,
            "queries": queries,
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if result.failed_items else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect precedent rows for CaseLens.")
    parser.add_argument("--scope", default="damages", help="Collection scope label.")
    parser.add_argument("--priority", default="P0", help="Comma-separated priorities, e.g. P0 or P0,P1.")
    parser.add_argument("--include-keywords", action="store_true", help="Also run StatuteScope keyword queries.")
    parser.add_argument("--query", help="Run one explicit precedent search query.")
    parser.add_argument("--limit", type=int, default=300, help="Maximum unique precedents to fetch.")
    parser.add_argument("--display", type=int, default=100, help="Search results per page.")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum pages per query.")
    parser.add_argument("--dry-run", action="store_true", help="Print mapped rows without DB upsert.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    parser.add_argument("--pause-seconds", type=float, default=0.15, help="Pause between API calls.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
