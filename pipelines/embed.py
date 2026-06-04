from __future__ import annotations

import argparse
import json
import os
from typing import Any

from pipelines.common.embedding import (
    DEFAULT_OPENAI_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    content_hash,
    embed_text,
    embedding_model_name,
    vector_literal,
)
from pipelines.common.env import load_dotenv


CASE_LEVEL_TYPES = ("facts", "issue", "material_facts", "combined")


def embed_preview(
    text: str,
    *,
    provider: str = "local",
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    vector = embed_text(text, provider=provider, model=model, api_key=api_key)
    effective_model = embedding_model_name(provider=provider, model=model, api_key=api_key)
    return {
        "embedding_provider": provider,
        "embedding_model": effective_model,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "content_hash": content_hash(text),
        "vector_prefix": vector[:8],
        "non_zero": sum(1 for value in vector if value != 0),
    }


def embed_cases(
    database_url: str,
    limit: int | None,
    overwrite: bool,
    *,
    provider: str = "local",
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            case_rows = load_case_embedding_inputs(cursor, limit)
            paragraph_rows = load_paragraph_embedding_inputs(cursor, limit)

            upserted = 0
            effective_model = embedding_model_name(provider=provider, model=model, api_key=api_key)
            for row in case_rows:
                case_id = row["case_id"]
                for embedding_type, content_text in build_case_contents(row):
                    if not content_text.strip():
                        continue
                    upsert_embedding(
                        cursor,
                        case_id=case_id,
                        paragraph_id=None,
                        embedding_type=embedding_type,
                        content_text=content_text,
                        overwrite=overwrite,
                        provider=provider,
                        model=model,
                        api_key=api_key,
                        effective_model=effective_model,
                    )
                    upserted += 1

            for row in paragraph_rows:
                if not row["text"].strip():
                    continue
                upsert_embedding(
                    cursor,
                    case_id=row["case_id"],
                    paragraph_id=row["paragraph_uuid"],
                    embedding_type="paragraph",
                    content_text=row["text"],
                    overwrite=overwrite,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    effective_model=effective_model,
                )
                upserted += 1

            cursor.execute(
                """
                insert into pipeline_runs (
                  stage, status, source, params, finished_at,
                  input_count, success_count, failed_count
                )
                values ('embed', 'succeeded', 'internal_db', %s, now(), %s, %s, 0)
                """,
                (
                    Jsonb(
                        {
                            "limit": limit,
                            "overwrite": overwrite,
                            "embedding_provider": provider,
                            "embedding_model": effective_model,
                            "embedding_dimension": EMBEDDING_DIMENSION,
                        }
                    ),
                    len(case_rows) + len(paragraph_rows),
                    upserted,
                ),
            )
        conn.commit()

    return {
        "case_inputs": len(case_rows),
        "paragraph_inputs": len(paragraph_rows),
        "embeddings_upserted": upserted,
    }


def load_case_embedding_inputs(cursor: Any, limit: int | None) -> list[dict[str, Any]]:
    limit_sql = "limit %s" if limit else ""
    cursor.execute(
        f"""
        select distinct on (cases.id)
          cases.id as case_id,
          case_structures.facts,
          case_structures.legal_issue,
          case_structures.court_reasoning,
          case_structures.conclusion,
          case_structures.material_facts,
          case_structures.outcome
        from cases
        join case_structures on case_structures.case_id = cases.id
        where cases.is_deleted = false
        order by cases.id, case_structures.processed_at desc
        {limit_sql}
        """,
        (limit,) if limit else (),
    )
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def load_paragraph_embedding_inputs(cursor: Any, limit: int | None) -> list[dict[str, Any]]:
    limit_sql = "limit %s" if limit else ""
    cursor.execute(
        f"""
        select
          cases.id as case_id,
          case_paragraphs.id as paragraph_uuid,
          case_paragraphs.text
        from case_paragraphs
        join cases on cases.id = case_paragraphs.case_id
        where cases.is_deleted = false
        order by cases.collected_at desc, case_paragraphs.paragraph_order asc
        {limit_sql}
        """,
        (limit,) if limit else (),
    )
    columns = [column.name for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def build_case_contents(row: dict[str, Any]) -> list[tuple[str, str]]:
    facts = str(row.get("facts") or "")
    issue = str(row.get("legal_issue") or "")
    reasoning = str(row.get("court_reasoning") or "")
    conclusion = str(row.get("conclusion") or "")
    material_facts = json.dumps(row.get("material_facts") or {}, ensure_ascii=False, sort_keys=True)
    outcome = json.dumps(row.get("outcome") or {}, ensure_ascii=False, sort_keys=True)
    combined = "\n".join(
        part
        for part in [facts, issue, reasoning, conclusion, material_facts, outcome]
        if part.strip()
    )
    return [
        ("facts", facts),
        ("issue", issue),
        ("material_facts", material_facts),
        ("combined", combined),
    ]


def upsert_embedding(
    cursor: Any,
    *,
    case_id: Any,
    paragraph_id: Any | None,
    embedding_type: str,
    content_text: str,
    overwrite: bool,
    provider: str,
    model: str | None,
    api_key: str | None,
    effective_model: str,
) -> None:
    hash_value = content_hash(content_text)
    if overwrite:
        cursor.execute(
            """
            delete from case_embeddings
            where case_id = %s
              and embedding_type = %s
              and embedding_model = %s
              and (
                (%s::uuid is null and paragraph_id is null)
                or paragraph_id = %s::uuid
              )
            """,
            (case_id, embedding_type, effective_model, paragraph_id, paragraph_id),
        )

    if paragraph_id is None:
        cursor.execute(
            """
            select 1
            from case_embeddings
            where case_id = %s
              and paragraph_id is null
              and embedding_type = %s
              and embedding_model = %s
              and content_hash = %s
            limit 1
            """,
            (case_id, embedding_type, effective_model, hash_value),
        )
    else:
        cursor.execute(
            """
            select 1
            from case_embeddings
            where case_id = %s
              and paragraph_id = %s
              and embedding_type = %s
              and embedding_model = %s
              and content_hash = %s
            limit 1
            """,
            (case_id, paragraph_id, embedding_type, effective_model, hash_value),
        )
    if cursor.fetchone():
        return

    cursor.execute(
        """
        insert into case_embeddings (
          case_id, paragraph_id, embedding_type, embedding_model,
          embedding_dimension, content_text, content_hash, embedding,
          needs_regeneration
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s::vector, false)
        """,
        (
            case_id,
            paragraph_id,
            embedding_type,
            effective_model,
            EMBEDDING_DIMENSION,
            content_text,
            hash_value,
            vector_literal(embed_text(content_text, provider=provider, model=model, api_key=api_key)),
        ),
    )


def run(args: argparse.Namespace) -> int:
    load_dotenv()
    provider = args.provider or os.getenv("EMBEDDING_PROVIDER", "local")
    model = args.model or os.getenv("EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL)
    api_key = os.getenv("OPENAI_API_KEY")
    if args.dry_run_text:
        print(
            json.dumps(
                embed_preview(args.dry_run_text, provider=provider, model=model, api_key=api_key),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    database_url = os.getenv("DATABASE_URL", "postgresql://caselens:caselens@localhost:5432/caselens")
    summary = embed_cases(
        database_url,
        args.limit,
        args.overwrite,
        provider=provider,
        model=model,
        api_key=api_key,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create deterministic fallback embeddings.")
    parser.add_argument("--limit", type=int, help="Maximum cases and paragraphs to embed.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing embeddings for the selected model.")
    parser.add_argument("--dry-run-text", help="Embed a text value without touching the DB.")
    parser.add_argument(
        "--provider",
        choices=["local", "openai", "sentence-transformers", "huggingface"],
        help="Embedding provider override.",
    )
    parser.add_argument("--model", help="Embedding model override.")
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
