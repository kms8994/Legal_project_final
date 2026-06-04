from __future__ import annotations

from dataclasses import dataclass
import re

from app.core.config import settings
from pipelines.common.embedding import embed_text, embedding_model_name, vector_literal

from app.repositories.statute_search import CaseSearchRow, StatuteSearchRepository
from app.schemas.search import (
    NaturalSearchResponse,
    Pagination,
    ParsedIntent,
    SearchEvidenceSnippet,
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
        evidence_by_case = _evidence_by_case(rows)
        snippets_by_case = self.repository.evidence_snippets_for_cases(
            [row.case_id for row in rows],
            evidence_by_case,
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
            results=[
                _to_result_card(
                    row,
                    index,
                    evidence_snippets=snippets_by_case.get(row.case_id, []),
                )
                for index, row in enumerate(rows)
            ],
        )

    def search_natural(self, *, query: str, page: int, size: int) -> NaturalSearchResponse:
        intent = _parse_intent(query)
        query_vector = embed_text(
            query,
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        effective_model = embedding_model_name(
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        embedding_scores = self.repository.embedding_scores_for_query(
            vector_literal(query_vector),
            effective_model,
        )
        scored_rows = _rank_rows(
            query,
            intent,
            self.repository.list_cases_for_natural_search(),
            embedding_scores=embedding_scores,
        )
        offset = (page - 1) * size
        page_rows = scored_rows[offset : offset + size]
        rows = [row for row, _score in page_rows]
        evidence_by_case = _evidence_by_case(rows)
        snippets_by_case = self.repository.evidence_snippets_for_cases(
            [row.case_id for row in rows],
            evidence_by_case,
        )

        return NaturalSearchResponse(
            parsed_intent=intent,
            pagination=Pagination(
                page=page,
                size=size,
                total=len(scored_rows),
                has_next=page * size < len(scored_rows),
            ),
            results=[
                _to_result_card(
                    row,
                    index,
                    score=score,
                    evidence_snippets=snippets_by_case.get(row.case_id, []),
                )
                for index, (row, score) in enumerate(page_rows)
            ],
        )


def _to_result_card(
    row: CaseSearchRow,
    index: int,
    score: float | None = None,
    evidence_snippets: list[object] | None = None,
) -> SearchResultCard:
    confidence = row.confidence_score
    evidence_ids = _evidence_ids(row.evidence_spans)
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
        score=score if score is not None else max(0.0, min(1.0, confidence - (index * 0.01))),
        evidence_ids=evidence_ids,
        evidence_snippets=[
            SearchEvidenceSnippet(
                evidence_id=snippet.evidence_id,
                section_type=snippet.section_type,
                paragraph_order=snippet.paragraph_order,
                text=snippet.text,
            )
            for snippet in (evidence_snippets or [])
            if snippet.evidence_id in evidence_ids
        ],
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
        ids.extend(_extract_evidence_ids(value))
    return ids[:5]


def _extract_evidence_ids(value: object) -> list[str]:
    if isinstance(value, str):
        return [_normalize_evidence_id(value)]
    if isinstance(value, list):
        ids: list[str] = []
        for item in value:
            ids.extend(_extract_evidence_ids(item))
        return ids
    if isinstance(value, dict):
        paragraph_id = value.get("paragraph_id")
        if isinstance(paragraph_id, str):
            return [_normalize_evidence_id(paragraph_id)]
    return []


def _normalize_evidence_id(value: str) -> str:
    if len(value) == 4 and value.startswith("P") and value[1:].isdigit():
        return f"P{int(value[1:]):04d}"
    return value


def _evidence_by_case(rows: list[CaseSearchRow]) -> dict[str, list[str]]:
    return {row.case_id: _evidence_ids(row.evidence_spans) for row in rows}


def _parse_intent(query: str) -> ParsedIntent:
    compact = " ".join(query.split())
    keywords = _keywords(compact)
    inferred_articles = _infer_articles(compact)
    legal_domain = (
        "damages"
        if _contains_any(compact, ["damage", "\uc190\ud574", "\ubc30\uc0c1"])
        else None
    )
    case_type = "civil" if legal_domain == "damages" else None
    confidence = 0.45
    if keywords:
        confidence += min(0.25, len(keywords) * 0.04)
    if inferred_articles:
        confidence += 0.2
    if legal_domain:
        confidence += 0.1
    confidence = min(0.95, confidence)

    return ParsedIntent(
        case_type=case_type,
        legal_domain=legal_domain,
        keywords=keywords,
        legal_issue=_issue(compact, keywords),
        inferred_articles=inferred_articles,
        inferred_articles_validated=bool(inferred_articles),
        facts_summary=compact[:240],
        confidence=round(confidence, 3),
        needs_clarification=confidence < 0.5,
        clarification_question=(
            "Add the accident type, disputed conduct, or statute."
            if confidence < 0.5
            else None
        ),
    )


def _keywords(query: str) -> list[str]:
    tokens = [
        token.lower()
        for token in re.findall(r"[0-9A-Za-z가-힣_]+", query)
        if len(token) >= 2
    ]
    stopwords = {
        "case",
        "search",
        "find",
        "\ud310\ub840",
        "\uac80\uc0c9",
        "\uad00\ub828",
    }
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        if token in stopwords or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result[:12]


def _infer_articles(query: str) -> list[str]:
    inferred: list[str] = []
    rules = [
        (["750", "\uc81c750", "\ubd88\ubc95\ud589\uc704", "\uc190\ud574\ubc30\uc0c1"], "civil_act_750"),
        (["751", "\uc81c751", "\uc704\uc790\ub8cc", "\uba85\uc608"], "civil_act_751"),
        (["396", "\uc81c396", "\uacfc\uc2e4\uc0c1\uacc4", "\uacfc\uc2e4"], "civil_act_396"),
    ]
    lowered = query.lower()
    for needles, article in rules:
        if any(needle in lowered for needle in needles):
            inferred.append(article)
    return inferred


def _issue(query: str, keywords: list[str]) -> str | None:
    if _contains_any(query, ["traffic", "accident", "\uad50\ud1b5", "\uc0ac\uace0"]):
        return "traffic accident liability and damages"
    if _contains_any(query, ["defamation", "\uba85\uc608", "\uc704\uc790\ub8cc"]):
        return "defamation and non-property damages"
    if keywords:
        return "structured keyword search"
    return None


def _rank_rows(
    query: str,
    intent: ParsedIntent,
    rows: list[CaseSearchRow],
    *,
    embedding_scores: dict[str, float] | None = None,
) -> list[tuple[CaseSearchRow, float]]:
    query_terms = set(intent.keywords)
    embedding_scores = embedding_scores or {}
    ranked: list[tuple[CaseSearchRow, float]] = []
    for row in rows:
        text = " ".join(
            str(value or "")
            for value in [
                row.case_name,
                row.legal_domain,
                row.case_type,
                row.facts,
                row.conclusion,
                " ".join(row.cited_articles),
                " ".join(str(item) for item in row.outcome.values()),
            ]
        ).lower()
        text_terms = set(re.findall(r"[0-9A-Za-z가-힣_]+", text))
        keyword_score = _overlap(query_terms, text_terms)
        article_score = _overlap(set(intent.inferred_articles), set(row.cited_articles))
        domain_score = 1.0 if intent.legal_domain and intent.legal_domain in text else 0.0
        fuzzy_score = 1.0 if query.lower() in text else 0.0
        embedding_score = embedding_scores.get(row.case_id, 0.0)
        score = min(
            1.0,
            (keyword_score * 0.31)
            + (article_score * 0.2)
            + (domain_score * 0.1)
            + (fuzzy_score * 0.04)
            + (embedding_score * 0.2)
            + (row.confidence_score * 0.15),
        )
        if score > 0 or not query_terms:
            ranked.append((row, round(score, 3)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def _overlap(left: set[str], right: set[str]) -> float:
    if not left:
        return 0.0
    return len(left & right) / len(left)


def _contains_any(value: str, needles: list[str]) -> bool:
    lowered = value.lower()
    return any(needle in lowered for needle in needles)
