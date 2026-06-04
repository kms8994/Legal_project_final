from __future__ import annotations

from dataclasses import dataclass

from app.repositories.statute_search import CaseSearchRow, StatuteSearchRepository
from app.schemas.search import (
    Pagination,
    SearchResultCard,
    StatuteQueryInfo,
    StatuteSearchResponse,
)
from app.services.article_normalizer import ArticleParseError, parse_article_ref


class ArticleNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class StatuteSearchService:
    repository: StatuteSearchRepository

    def search(self, *, query: str, page: int, size: int, sort: str) -> StatuteSearchResponse:
        try:
            parsed = parse_article_ref(query)
        except ArticleParseError:
            raise

        article = self.repository.resolve_article(parsed.law_name, parsed.article_no)
        if article is None:
            raise ArticleNotFoundError(parsed.normalized_ref)

        total = self.repository.count_cases_for_article(article.normalized_ref)
        rows = self.repository.search_cases_for_article(
            article.normalized_ref,
            page=page,
            size=size,
            sort=sort,
        )

        return StatuteSearchResponse(
            query=StatuteQueryInfo(
                raw=query,
                normalized_ref=article.normalized_ref,
                law_name=article.law_name,
                article_no=str(article.article_no),
                article_validated=True,
            ),
            pagination=Pagination(
                page=page,
                size=size,
                total=total,
                has_next=page * size < total,
            ),
            results=[_to_result_card(row, index) for index, row in enumerate(rows)],
        )


def _to_result_card(row: CaseSearchRow, index: int) -> SearchResultCard:
    confidence = row.confidence_score
    return SearchResultCard(
        case_id=row.case_id,
        case_no=row.case_no,
        court_name=row.court_name,
        court_level=row.court_level,
        decision_date=row.decision_date,
        case_name=row.case_name,
        case_type=row.case_type,
        legal_domain=row.legal_domain,
        summary_card=_summary(row),
        outcome=row.outcome,
        cited_articles=row.cited_articles,
        score=max(0.0, min(1.0, confidence - (index * 0.01))),
        evidence_ids=_evidence_ids(row.evidence_spans),
        source_url=row.source_url,
        review_status=row.review_status,
        confidence_score=confidence,
    )


def _summary(row: CaseSearchRow) -> str:
    source = row.conclusion or row.facts or row.case_name
    compact = " ".join(str(source).split())
    if len(compact) <= 120:
        return compact
    return f"{compact[:117]}..."


def _evidence_ids(evidence_spans: dict[str, object]) -> list[str]:
    ids: list[str] = []
    for value in evidence_spans.values():
        if isinstance(value, list):
            ids.extend(item for item in value if isinstance(item, str))
    return ids[:5]
