from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass(frozen=True)
class CaseMetaRecord:
    case_id: str
    external_id: str
    case_no: str
    court_name: str
    court_level: str | None
    decision_date: date | None
    case_name: str
    case_type: str | None
    legal_domain: str | None
    source_url: str | None
    collected_at: datetime


@dataclass(frozen=True)
class CaseStructureRecord:
    facts: str | None
    legal_issue: str | None
    court_reasoning: str | None
    conclusion: str | None
    material_facts: dict[str, Any]
    outcome: dict[str, Any]
    cited_articles: list[str]
    facets: dict[str, Any]
    evidence_spans: dict[str, Any]
    confidence_score: float
    review_status: str


@dataclass(frozen=True)
class CaseParagraphRecord:
    paragraph_id: str
    section_type: str
    paragraph_order: int
    text: str
    char_start: int | None
    char_end: int | None


@dataclass(frozen=True)
class CompareCandidateRecord:
    case_id: str
    case_no: str
    court_name: str
    decision_date: date | None
    case_name: str
    legal_domain: str | None
    facts: str | None
    legal_issue: str | None
    conclusion: str | None
    material_facts: dict[str, Any]
    outcome: dict[str, Any]
    cited_articles: list[str]
    facets: dict[str, Any]
    evidence_spans: dict[str, Any]
    confidence_score: float


class CaseDetailRepository(Protocol):
    def get_case(self, case_id: str) -> CaseMetaRecord | None:
        ...

    def get_structure(self, case_id: str) -> CaseStructureRecord | None:
        ...

    def list_paragraphs(self, case_id: str) -> list[CaseParagraphRecord]:
        ...

    def list_compare_candidates(self, case_id: str) -> list[CompareCandidateRecord]:
        ...

    def embedding_similarities_for_case(self, case_id: str, embedding_model: str) -> dict[str, float]:
        ...


class PostgresCaseDetailRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def get_case(self, case_id: str) -> CaseMetaRecord | None:
        row = self.connection.execute(
            text(
                """
                select
                  id::text as case_id,
                  external_id,
                  case_no,
                  court_name,
                  court_level,
                  decision_date,
                  case_name,
                  case_type,
                  legal_domain,
                  source_url,
                  collected_at
                from cases
                where id = :case_id
                  and is_deleted = false
                limit 1
                """
            ),
            {"case_id": case_id},
        ).mappings().first()

        if row is None:
            return None

        return CaseMetaRecord(
            case_id=row["case_id"],
            external_id=row["external_id"],
            case_no=row["case_no"],
            court_name=row["court_name"],
            court_level=row["court_level"],
            decision_date=row["decision_date"],
            case_name=row["case_name"],
            case_type=row["case_type"],
            legal_domain=row["legal_domain"],
            source_url=row["source_url"],
            collected_at=row["collected_at"],
        )

    def get_structure(self, case_id: str) -> CaseStructureRecord | None:
        row = self.connection.execute(
            text(
                """
                select
                  facts,
                  legal_issue,
                  court_reasoning,
                  conclusion,
                  material_facts,
                  outcome,
                  cited_articles,
                  facets,
                  evidence_spans,
                  confidence_score,
                  review_status
                from case_structures
                where case_id = :case_id
                order by processed_at desc
                limit 1
                """
            ),
            {"case_id": case_id},
        ).mappings().first()

        if row is None:
            return None

        return CaseStructureRecord(
            facts=row["facts"],
            legal_issue=row["legal_issue"],
            court_reasoning=row["court_reasoning"],
            conclusion=row["conclusion"],
            material_facts=_dict(row["material_facts"]),
            outcome=_dict(row["outcome"]),
            cited_articles=_cited_refs(row["cited_articles"]),
            facets=_dict(row["facets"]),
            evidence_spans=_dict(row["evidence_spans"]),
            confidence_score=float(row["confidence_score"]),
            review_status=row["review_status"],
        )

    def list_paragraphs(self, case_id: str) -> list[CaseParagraphRecord]:
        rows = self.connection.execute(
            text(
                """
                select
                  paragraph_id,
                  section_type,
                  paragraph_order,
                  text,
                  char_start,
                  char_end
                from case_paragraphs
                where case_id = :case_id
                order by paragraph_order asc
                """
            ),
            {"case_id": case_id},
        ).mappings().all()

        return [
            CaseParagraphRecord(
                paragraph_id=row["paragraph_id"],
                section_type=row["section_type"],
                paragraph_order=row["paragraph_order"],
                text=row["text"],
                char_start=row["char_start"],
                char_end=row["char_end"],
            )
            for row in rows
        ]

    def list_compare_candidates(self, case_id: str) -> list[CompareCandidateRecord]:
        rows = self.connection.execute(
            text(
                """
                with latest_structures as (
                  select distinct on (case_id)
                    case_id,
                    facts,
                    legal_issue,
                    conclusion,
                    material_facts,
                    outcome,
                    cited_articles,
                    facets,
                    evidence_spans,
                    confidence_score
                  from case_structures
                  order by case_id, processed_at desc
                )
                select
                  cases.id::text as case_id,
                  cases.case_no,
                  cases.court_name,
                  cases.decision_date,
                  cases.case_name,
                  cases.legal_domain,
                  latest_structures.facts,
                  latest_structures.legal_issue,
                  latest_structures.conclusion,
                  latest_structures.material_facts,
                  latest_structures.outcome,
                  latest_structures.cited_articles,
                  latest_structures.facets,
                  latest_structures.evidence_spans,
                  latest_structures.confidence_score
                from latest_structures
                join cases on cases.id = latest_structures.case_id
                where cases.id <> :case_id
                  and cases.is_deleted = false
                """
            ),
            {"case_id": case_id},
        ).mappings().all()

        return [
            CompareCandidateRecord(
                case_id=row["case_id"],
                case_no=row["case_no"],
                court_name=row["court_name"],
                decision_date=row["decision_date"],
                case_name=row["case_name"],
                legal_domain=row["legal_domain"],
                facts=row["facts"],
                legal_issue=row["legal_issue"],
                conclusion=row["conclusion"],
                material_facts=_dict(row["material_facts"]),
                outcome=_dict(row["outcome"]),
                cited_articles=_cited_refs(row["cited_articles"]),
                facets=_dict(row["facets"]),
                evidence_spans=_dict(row["evidence_spans"]),
                confidence_score=float(row["confidence_score"]),
            )
            for row in rows
        ]

    def embedding_similarities_for_case(self, case_id: str, embedding_model: str) -> dict[str, float]:
        rows = self.connection.execute(
            text(
                """
                select
                  candidate.case_id::text,
                  greatest(0.0, 1.0 - (base.embedding <=> candidate.embedding)) as score
                from case_embeddings base
                join case_embeddings candidate
                  on candidate.embedding_type = base.embedding_type
                 and candidate.embedding_model = base.embedding_model
                 and candidate.case_id <> base.case_id
                join cases on cases.id = candidate.case_id
                where base.case_id = :case_id
                  and base.embedding_type = 'combined'
                  and base.embedding_model = :embedding_model
                  and base.needs_regeneration = false
                  and candidate.needs_regeneration = false
                  and cases.is_deleted = false
                """
            ),
            {"case_id": case_id, "embedding_model": embedding_model},
        ).all()
        return {case_id: float(score) for case_id, score in rows}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _cited_refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    refs: list[str] = []
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("normalized_ref"), str):
            refs.append(item["normalized_ref"])
        elif isinstance(item, str):
            refs.append(item)
    return refs
