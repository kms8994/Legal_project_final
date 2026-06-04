from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import Any

from pipelines.common.env import load_dotenv
from pipelines.common.extract import ExtractedCase, extract_case_features


def extract_preview(text: str) -> dict[str, Any]:
    return asdict(extract_case_features(text))


def extract_cases(database_url: str, limit: int | None) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            law_aliases = load_law_aliases(cursor)
            known_articles = load_known_articles(cursor)
            limit_sql = "limit %s" if limit else ""
            cursor.execute(
                f"""
                select id, raw_text, case_type, court_level
                from cases
                where raw_text <> ''
                order by collected_at desc
                {limit_sql}
                """,
                (limit,) if limit else None,
            )
            rows: list[tuple[Any, str, str | None, str | None]] = cursor.fetchall()

            upserted = 0
            failed = 0
            for case_id, raw_text, case_type, court_level in rows:
                extracted = extract_case_features(
                    raw_text,
                    case_type=case_type,
                    court_level=court_level,
                    law_aliases=law_aliases,
                    known_articles=known_articles,
                )
                if not extracted.cited_articles and extracted.outcome.get("disposition") == "unknown":
                    failed += 1
                upsert_structure(cursor, case_id, extracted)
                upserted += cursor.rowcount

            cursor.execute(
                """
                insert into pipeline_runs (
                  stage, status, source, params, finished_at,
                  input_count, success_count, failed_count
                )
                values ('extract', %s, 'internal_db', %s, now(), %s, %s, %s)
                """,
                (
                    "succeeded" if failed == 0 else "partial_failed",
                    Jsonb({"limit": limit}),
                    len(rows),
                    upserted,
                    failed,
                ),
            )
        conn.commit()

    return {"input_count": len(rows), "structures_upserted": upserted, "failed_count": failed}


def load_law_aliases(cursor: Any) -> dict[str, str]:
    cursor.execute(
        """
        select law_aliases.alias, laws.official_name
        from law_aliases
        join laws on laws.id = law_aliases.law_id
        """
    )
    return {alias: official_name for alias, official_name in cursor.fetchall()}


def load_known_articles(cursor: Any) -> set[str]:
    cursor.execute("select normalized_ref from articles")
    return {row[0] for row in cursor.fetchall()}


def upsert_structure(cursor: Any, case_id: Any, extracted: ExtractedCase) -> None:
    from psycopg.types.json import Jsonb

    cursor.execute(
        """
        insert into case_structures (
          case_id, cited_articles, outcome, facets, evidence_spans,
          confidence_score, review_status, prompt_version, model_name,
          structure_hash
        )
        values (%s, %s, %s, %s, %s, %s, %s, 'rule-extract-v1', 'rules', %s)
        on conflict (case_id, structure_hash) do update set
          cited_articles = excluded.cited_articles,
          outcome = excluded.outcome,
          facets = excluded.facets,
          evidence_spans = excluded.evidence_spans,
          confidence_score = excluded.confidence_score,
          review_status = excluded.review_status,
          processed_at = now()
        """,
        (
            case_id,
            Jsonb(extracted.cited_articles),
            Jsonb(extracted.outcome),
            Jsonb(extracted.facets),
            Jsonb(extracted.evidence_spans),
            extracted.confidence_score,
            "pending" if extracted.confidence_score < 0.7 else "auto_extracted",
            extracted.structure_hash,
        ),
    )


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    if args.dry_run_text:
        print(json.dumps(extract_preview(args.dry_run_text), ensure_ascii=False, indent=2))
        return 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = extract_cases(database_url, args.limit)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract rule-based CaseLens case structure candidates.")
    parser.add_argument("--limit", type=int, help="Maximum cases to extract.")
    parser.add_argument("--dry-run-text", help="Extract from a text value without touching the DB.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
