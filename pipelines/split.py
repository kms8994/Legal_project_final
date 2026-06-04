from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import Any

from pipelines.common.env import load_dotenv
from pipelines.common.text import Paragraph, split_case_text


def split_cases(database_url: str, limit: int | None, overwrite: bool) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    limit_sql = "limit %s" if limit else ""
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                select id, raw_text
                from cases
                where raw_text <> ''
                  and (
                    %s
                    or not exists (
                      select 1
                      from case_paragraphs
                      where case_paragraphs.case_id = cases.id
                    )
                  )
                order by collected_at desc
                {limit_sql}
                """,
                (overwrite, limit) if limit else (overwrite,),
            )
            rows: list[tuple[Any, str]] = cursor.fetchall()

            cases_processed = 0
            paragraphs_upserted = 0
            for case_id, raw_text in rows:
                paragraphs = split_case_text(raw_text)
                if not paragraphs:
                    continue
                if overwrite:
                    cursor.execute("delete from case_paragraphs where case_id = %s", (case_id,))
                for paragraph in paragraphs:
                    upsert_paragraph(cursor, case_id, paragraph)
                    paragraphs_upserted += cursor.rowcount
                cases_processed += 1

            cursor.execute(
                """
                insert into pipeline_runs (
                  stage, status, source, params, finished_at,
                  input_count, success_count, failed_count
                )
                values ('split', 'succeeded', 'internal_db', %s, now(), %s, %s, 0)
                """,
                (
                    Jsonb({"limit": limit, "overwrite": overwrite}),
                    len(rows),
                    paragraphs_upserted,
                ),
            )
        conn.commit()

    return {
        "input_count": len(rows),
        "cases_processed": cases_processed,
        "paragraphs_upserted": paragraphs_upserted,
    }


def upsert_paragraph(cursor: Any, case_id: Any, paragraph: Paragraph) -> None:
    cursor.execute(
        """
        insert into case_paragraphs (
          case_id, paragraph_id, section_type, paragraph_order,
          text, char_start, char_end, content_hash
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (case_id, paragraph_id) do update set
          section_type = excluded.section_type,
          paragraph_order = excluded.paragraph_order,
          text = excluded.text,
          char_start = excluded.char_start,
          char_end = excluded.char_end,
          content_hash = excluded.content_hash
        """,
        (
            case_id,
            paragraph.paragraph_id,
            paragraph.section_type,
            paragraph.paragraph_order,
            paragraph.text,
            paragraph.char_start,
            paragraph.char_end,
            paragraph.content_hash,
        ),
    )


def dry_run(text: str, max_paragraphs: int) -> dict[str, Any]:
    paragraphs = split_case_text(text)
    return {
        "paragraph_count": len(paragraphs),
        "paragraphs": [asdict(paragraph) for paragraph in paragraphs[:max_paragraphs]],
    }


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    if args.dry_run_text:
        print(json.dumps(dry_run(args.dry_run_text, args.max_paragraphs), ensure_ascii=False, indent=2))
        return 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = split_cases(database_url, args.limit, args.overwrite)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Split normalized CaseLens case text into paragraphs.")
    parser.add_argument("--limit", type=int, help="Maximum cases to split.")
    parser.add_argument("--overwrite", action="store_true", help="Delete and recreate existing paragraphs.")
    parser.add_argument("--dry-run-text", help="Split a text value without touching the DB.")
    parser.add_argument("--max-paragraphs", type=int, default=20, help="Dry-run paragraph preview count.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
