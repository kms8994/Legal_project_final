from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import Any

from pipelines.common.env import load_dotenv
from pipelines.common.validate import validate_structure


def validate_preview(payload: str, known_articles: set[str], text_length: int | None) -> dict[str, Any]:
    structure = json.loads(payload)
    return asdict(validate_structure(structure, known_articles, text_length))


def validate_cases(database_url: str, limit: int | None) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            known_articles = load_known_articles(cursor)
            limit_sql = "limit %s" if limit else ""
            cursor.execute(
                f"""
                select
                  case_structures.id,
                  case_structures.cited_articles,
                  case_structures.outcome,
                  case_structures.facets,
                  case_structures.evidence_spans,
                  case_structures.confidence_score,
                  length(cases.raw_text) as text_length
                from case_structures
                join cases on cases.id = case_structures.case_id
                where case_structures.is_reviewed = false
                order by case_structures.processed_at desc
                {limit_sql}
                """,
                (limit,) if limit else None,
            )
            rows = cursor.fetchall()

            valid_count = 0
            needs_review_count = 0
            invalid_count = 0
            for row in rows:
                structure_id = row[0]
                structure = {
                    "cited_articles": row[1],
                    "outcome": row[2],
                    "facets": row[3],
                    "evidence_spans": row[4],
                    "confidence_score": row[5],
                }
                result = validate_structure(structure, known_articles, row[6])
                evidence_spans = dict(structure["evidence_spans"] or {})
                evidence_spans["validation"] = {
                    "status": result.review_status,
                    "reasons": result.reasons,
                }
                cursor.execute(
                    """
                    update case_structures
                    set review_status = %s,
                        confidence_score = %s,
                        evidence_spans = %s,
                        processed_at = now()
                    where id = %s
                    """,
                    (
                        result.review_status,
                        result.confidence_score,
                        Jsonb(evidence_spans),
                        structure_id,
                    ),
                )
                if result.review_status == "auto_validated":
                    valid_count += 1
                elif result.review_status == "invalid":
                    invalid_count += 1
                else:
                    needs_review_count += 1

            cursor.execute(
                """
                insert into pipeline_runs (
                  stage, status, source, params, finished_at,
                  input_count, success_count, failed_count, error_summary
                )
                values ('validate', %s, 'internal_db', %s, now(), %s, %s, %s, %s)
                """,
                (
                    "succeeded" if invalid_count == 0 else "partial_failed",
                    Jsonb({"limit": limit}),
                    len(rows),
                    valid_count,
                    needs_review_count + invalid_count,
                    json.dumps(
                        {
                            "needs_review_count": needs_review_count,
                            "invalid_count": invalid_count,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
        conn.commit()

    return {
        "input_count": len(rows),
        "auto_validated": valid_count,
        "needs_review": needs_review_count,
        "invalid": invalid_count,
    }


def load_known_articles(cursor: Any) -> set[str]:
    cursor.execute("select normalized_ref from articles")
    return {row[0] for row in cursor.fetchall()}


def parse_known_articles(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    if args.dry_run_json:
        known_articles = parse_known_articles(args.known_articles)
        result = validate_preview(args.dry_run_json, known_articles, args.text_length)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = validate_cases(database_url, args.limit)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate extracted CaseLens structures.")
    parser.add_argument("--limit", type=int, help="Maximum structures to validate.")
    parser.add_argument("--dry-run-json", help="Validate a JSON structure without touching the DB.")
    parser.add_argument("--known-articles", help="Comma-separated normalized refs for dry-run.")
    parser.add_argument("--text-length", type=int, help="Raw text length for evidence offset validation.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
