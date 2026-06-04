from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from pipelines.common.env import load_dotenv
from pipelines.common.text import normalize_case_text, source_hash


@dataclass(frozen=True)
class NormalizePreview:
    input_length: int
    output_length: int
    source_hash: str
    text: str


def normalize_preview(text: str, max_chars: int) -> NormalizePreview:
    normalized = normalize_case_text(text)
    return NormalizePreview(
        input_length=len(text),
        output_length=len(normalized),
        source_hash=source_hash(normalized),
        text=normalized[:max_chars],
    )


def normalize_cases(database_url: str, limit: int | None, only_empty_hash: bool) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    where = "where raw_text <> ''"
    if only_empty_hash:
        where += " and (source_hash is null or source_hash = '')"
    limit_sql = "limit %s" if limit else ""

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                select id, raw_text
                from cases
                {where}
                order by collected_at desc
                {limit_sql}
                """,
                (limit,) if limit else None,
            )
            rows: list[tuple[Any, str]] = cursor.fetchall()

            updated = 0
            for case_id, raw_text in rows:
                normalized = normalize_case_text(raw_text)
                if not normalized:
                    continue
                cursor.execute(
                    """
                    update cases
                    set raw_text = %s,
                        source_hash = %s,
                        updated_at = now()
                    where id = %s
                    """,
                    (normalized, source_hash(normalized), case_id),
                )
                updated += cursor.rowcount

            cursor.execute(
                """
                insert into pipeline_runs (
                  stage, status, source, params, finished_at,
                  input_count, success_count, failed_count
                )
                values ('normalize', 'succeeded', 'internal_db', %s, now(), %s, %s, 0)
                """,
                (Jsonb({"limit": limit, "only_empty_hash": only_empty_hash}), len(rows), updated),
            )
        conn.commit()

    return {"input_count": len(rows), "normalized_count": updated}


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    if args.dry_run_text:
        preview = normalize_preview(args.dry_run_text, args.max_chars)
        print(json.dumps(asdict(preview), ensure_ascii=False, indent=2))
        return 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = normalize_cases(database_url, args.limit, args.only_empty_hash)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize collected CaseLens precedent text.")
    parser.add_argument("--limit", type=int, help="Maximum cases to normalize.")
    parser.add_argument("--only-empty-hash", action="store_true", help="Only normalize rows missing source_hash.")
    parser.add_argument("--dry-run-text", help="Normalize a text value without touching the DB.")
    parser.add_argument("--max-chars", type=int, default=1000, help="Dry-run preview length.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
