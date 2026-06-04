from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from typing import Any

from pipelines.common.env import load_dotenv
from pipelines.common.structure import StructuredCase, structure_case_text


def structure_preview(text: str) -> dict[str, Any]:
    return asdict(structure_case_text(text))


def structure_cases(database_url: str, limit: int | None, overwrite: bool) -> dict[str, int]:
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
                  and (
                    %s
                    or not exists (
                      select 1
                      from case_structures
                      where case_structures.case_id = cases.id
                        and case_structures.model_name = 'rules'
                        and case_structures.prompt_version = 'rule-structure-v1'
                    )
                  )
                order by collected_at desc
                {limit_sql}
                """,
                (overwrite, limit) if limit else (overwrite,),
            )
            rows: list[tuple[Any, str, str | None, str | None]] = cursor.fetchall()

            upserted = 0
            needs_review = 0
            for case_id, raw_text, case_type, court_level in rows:
                structured = structure_case_text(
                    raw_text,
                    case_type=case_type,
                    court_level=court_level,
                    law_aliases=law_aliases,
                    known_articles=known_articles,
                )
                upsert_structure(cursor, case_id, structured)
                upserted += cursor.rowcount
                if structured.review_status == "pending":
                    needs_review += 1

            cursor.execute(
                """
                insert into pipeline_runs (
                  stage, status, source, params, finished_at,
                  input_count, success_count, failed_count
                )
                values ('structure', %s, 'internal_db', %s, now(), %s, %s, %s)
                """,
                (
                    "succeeded" if needs_review == 0 else "partial_failed",
                    Jsonb({"limit": limit, "overwrite": overwrite, "mode": "rule_fallback"}),
                    len(rows),
                    upserted,
                    needs_review,
                ),
            )
        conn.commit()

    return {
        "input_count": len(rows),
        "structures_upserted": upserted,
        "needs_review": needs_review,
    }


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


def upsert_structure(cursor: Any, case_id: Any, structured: StructuredCase) -> None:
    from psycopg.types.json import Jsonb

    cursor.execute(
        """
        insert into case_structures (
          case_id, cited_articles, facts, legal_issue, court_reasoning,
          conclusion, material_facts, aggravating_factors, mitigating_factors,
          key_disputed_facts, outcome, facets, evidence_spans,
          confidence_score, review_status, prompt_version, model_name,
          structure_hash
        )
        values (
          %s, %s, %s, %s, %s,
          %s, %s, %s, %s,
          %s, %s, %s, %s,
          %s, %s, 'rule-structure-v1', 'rules',
          %s
        )
        on conflict (case_id, structure_hash) do update set
          cited_articles = excluded.cited_articles,
          facts = excluded.facts,
          legal_issue = excluded.legal_issue,
          court_reasoning = excluded.court_reasoning,
          conclusion = excluded.conclusion,
          material_facts = excluded.material_facts,
          aggravating_factors = excluded.aggravating_factors,
          mitigating_factors = excluded.mitigating_factors,
          key_disputed_facts = excluded.key_disputed_facts,
          outcome = excluded.outcome,
          facets = excluded.facets,
          evidence_spans = excluded.evidence_spans,
          confidence_score = excluded.confidence_score,
          review_status = excluded.review_status,
          processed_at = now()
        """,
        (
            case_id,
            Jsonb(structured.cited_articles),
            structured.facts,
            structured.legal_issue,
            structured.court_reasoning,
            structured.conclusion,
            Jsonb(structured.material_facts),
            Jsonb(structured.aggravating_factors),
            Jsonb(structured.mitigating_factors),
            Jsonb(structured.key_disputed_facts),
            Jsonb(structured.outcome),
            Jsonb(structured.facets),
            Jsonb(structured.evidence_spans),
            structured.confidence_score,
            structured.review_status,
            structured.structure_hash,
        ),
    )


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    if args.dry_run_text:
        print(json.dumps(structure_preview(args.dry_run_text), ensure_ascii=False, indent=2))
        return 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = structure_cases(database_url, args.limit, args.overwrite)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create rule fallback structures for CaseLens cases.")
    parser.add_argument("--limit", type=int, help="Maximum cases to structure.")
    parser.add_argument("--overwrite", action="store_true", help="Recreate existing rule structures.")
    parser.add_argument("--dry-run-text", help="Structure a text value without touching the DB.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
