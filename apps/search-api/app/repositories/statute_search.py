from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass(frozen=True)
class ArticleRecord:
    normalized_ref: str
    law_name: str
    article_no: int


@dataclass(frozen=True)
class CaseSearchRow:
    case_id: str
    case_no: str
    court_name: str
    court_level: str | None
    decision_date: date | None
    case_name: str
    case_type: str | None
    legal_domain: str | None
    source_url: str | None
    cited_articles: list[str]
    facts: str | None
    conclusion: str | None
    outcome: dict[str, Any]
    evidence_spans: dict[str, Any]
    review_status: str
    confidence_score: float


@dataclass(frozen=True)
class SearchEvidenceRecord:
    case_id: str
    evidence_id: str
    section_type: str
    paragraph_order: int
    text: str


class StatuteSearchRepository(Protocol):
    def resolve_article(self, law_name: str, article_no: int) -> ArticleRecord | None:
        ...

    def count_cases_for_article(self, normalized_ref: str) -> int:
        ...

    def search_cases_for_article(
        self,
        normalized_ref: str,
        *,
        page: int,
        size: int,
        sort: str,
    ) -> list[CaseSearchRow]:
        ...

    def list_cases_for_natural_search(self) -> list[CaseSearchRow]:
        ...

    def embedding_scores_for_query(self, query_embedding: str, embedding_model: str) -> dict[str, float]:
        ...

    def evidence_snippets_for_cases(
        self,
        case_ids: list[str],
        evidence_ids_by_case: dict[str, list[str]],
    ) -> dict[str, list[SearchEvidenceRecord]]:
        ...


class PostgresStatuteSearchRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def resolve_article(self, law_name: str, article_no: int) -> ArticleRecord | None:
        row = self.connection.execute(
            text(
                """
                select
                  articles.normalized_ref,
                  laws.official_name as law_name,
                  articles.article_no
                from law_aliases
                join laws on laws.id = law_aliases.law_id
                join articles on articles.law_id = laws.id
                where law_aliases.alias = :law_name
                  and articles.article_no = :article_no
                order by articles.effective_date desc nulls last
                limit 1
                """
            ),
            {"law_name": law_name, "article_no": article_no},
        ).mappings().first()

        if row is None:
            return None

        return ArticleRecord(
            normalized_ref=row["normalized_ref"],
            law_name=row["law_name"],
            article_no=row["article_no"],
        )

    def count_cases_for_article(self, normalized_ref: str) -> int:
        payload = json.dumps([{"normalized_ref": normalized_ref}], ensure_ascii=False)
        row = self.connection.execute(
            text(
                """
                select count(*) as total
                from case_structures
                join cases on cases.id = case_structures.case_id
                where cases.is_deleted = false
                  and case_structures.cited_articles @> cast(:payload as jsonb)
                """
            ),
            {"payload": payload},
        ).mappings().one()
        return int(row["total"])

    def search_cases_for_article(
        self,
        normalized_ref: str,
        *,
        page: int,
        size: int,
        sort: str,
    ) -> list[CaseSearchRow]:
        payload = json.dumps([{"normalized_ref": normalized_ref}], ensure_ascii=False)
        order_by = (
            "cases.decision_date desc nulls last"
            if sort == "decision_date"
            else "case_structures.confidence_score desc, cases.decision_date desc nulls last"
        )
        offset = (page - 1) * size

        rows = self.connection.execute(
            text(
                f"""
                select
                  cases.id::text as case_id,
                  cases.case_no,
                  cases.court_name,
                  cases.court_level,
                  cases.decision_date,
                  cases.case_name,
                  cases.case_type,
                  cases.legal_domain,
                  cases.source_url,
                  case_structures.cited_articles,
                  case_structures.facts,
                  case_structures.conclusion,
                  case_structures.outcome,
                  case_structures.evidence_spans,
                  case_structures.review_status,
                  case_structures.confidence_score
                from case_structures
                join cases on cases.id = case_structures.case_id
                where cases.is_deleted = false
                  and case_structures.cited_articles @> cast(:payload as jsonb)
                order by {order_by}
                limit :size offset :offset
                """
            ),
            {"payload": payload, "size": size, "offset": offset},
        ).mappings().all()

        return [
            CaseSearchRow(
                case_id=row["case_id"],
                case_no=row["case_no"],
                court_name=row["court_name"],
                court_level=row["court_level"],
                decision_date=row["decision_date"],
                case_name=row["case_name"],
                case_type=row["case_type"],
                legal_domain=row["legal_domain"],
                source_url=row["source_url"],
                cited_articles=_extract_cited_refs(row["cited_articles"]),
                facts=row["facts"],
                conclusion=row["conclusion"],
                outcome=dict(row["outcome"] or {}),
                evidence_spans=dict(row["evidence_spans"] or {}),
                review_status=row["review_status"],
                confidence_score=float(row["confidence_score"]),
            )
            for row in rows
        ]

    def list_cases_for_natural_search(self) -> list[CaseSearchRow]:
        rows = self.connection.execute(
            text(
                """
                select
                  cases.id::text as case_id,
                  cases.case_no,
                  cases.court_name,
                  cases.court_level,
                  cases.decision_date,
                  cases.case_name,
                  cases.case_type,
                  cases.legal_domain,
                  cases.source_url,
                  case_structures.cited_articles,
                  case_structures.facts,
                  case_structures.conclusion,
                  case_structures.outcome,
                  case_structures.evidence_spans,
                  case_structures.review_status,
                  case_structures.confidence_score
                from case_structures
                join cases on cases.id = case_structures.case_id
                where cases.is_deleted = false
                order by case_structures.confidence_score desc, cases.decision_date desc nulls last
                limit 500
                """
            )
        ).mappings().all()

        return [
            CaseSearchRow(
                case_id=row["case_id"],
                case_no=row["case_no"],
                court_name=row["court_name"],
                court_level=row["court_level"],
                decision_date=row["decision_date"],
                case_name=row["case_name"],
                case_type=row["case_type"],
                legal_domain=row["legal_domain"],
                source_url=row["source_url"],
                cited_articles=_extract_cited_refs(row["cited_articles"]),
                facts=row["facts"],
                conclusion=row["conclusion"],
                outcome=dict(row["outcome"] or {}),
                evidence_spans=dict(row["evidence_spans"] or {}),
                review_status=row["review_status"],
                confidence_score=float(row["confidence_score"]),
            )
            for row in rows
        ]

    def embedding_scores_for_query(self, query_embedding: str, embedding_model: str) -> dict[str, float]:
        rows = self.connection.execute(
            text(
                """
                select
                  case_id::text,
                  greatest(0.0, 1.0 - (embedding <=> cast(:query_embedding as vector))) as score
                from case_embeddings
                where embedding_type = 'combined'
                  and embedding_model = :embedding_model
                  and needs_regeneration = false
                order by embedding <=> cast(:query_embedding as vector)
                limit 500
                """
            ),
            {"query_embedding": query_embedding, "embedding_model": embedding_model},
        ).all()
        return {case_id: float(score) for case_id, score in rows}

    def evidence_snippets_for_cases(
        self,
        case_ids: list[str],
        evidence_ids_by_case: dict[str, list[str]],
    ) -> dict[str, list[SearchEvidenceRecord]]:
        if not case_ids:
            return {}

        evidence_ids = sorted(
            {
                evidence_id
                for ids in evidence_ids_by_case.values()
                for evidence_id in ids
            }
        )
        if not evidence_ids:
            return {}

        rows = self.connection.execute(
            text(
                """
                select
                  case_id::text as case_id,
                  paragraph_id as evidence_id,
                  section_type,
                  paragraph_order,
                  text
                from case_paragraphs
                where case_id = any(cast(:case_ids as uuid[]))
                  and paragraph_id = any(cast(:evidence_ids as text[]))
                order by case_id, paragraph_order asc
                """
            ),
            {"case_ids": case_ids, "evidence_ids": evidence_ids},
        ).mappings().all()

        allowed = {
            case_id: set(ids)
            for case_id, ids in evidence_ids_by_case.items()
        }
        snippets: dict[str, list[SearchEvidenceRecord]] = {case_id: [] for case_id in case_ids}
        for row in rows:
            case_id = row["case_id"]
            evidence_id = row["evidence_id"]
            if evidence_id not in allowed.get(case_id, set()):
                continue
            snippets.setdefault(case_id, []).append(
                SearchEvidenceRecord(
                    case_id=case_id,
                    evidence_id=evidence_id,
                    section_type=row["section_type"],
                    paragraph_order=row["paragraph_order"],
                    text=row["text"],
                )
            )
        return snippets


def _extract_cited_refs(cited_articles: Any) -> list[str]:
    if not isinstance(cited_articles, list):
        return []
    refs: list[str] = []
    for article in cited_articles:
        if isinstance(article, dict) and isinstance(article.get("normalized_ref"), str):
            refs.append(article["normalized_ref"])
        elif isinstance(article, str):
            refs.append(article)
    return refs
