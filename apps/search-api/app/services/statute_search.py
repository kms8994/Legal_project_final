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
        primary_domain=_facet_string(row, "primary_domain"),
        secondary_domains=_facet_list(row, "secondary_domains"),
        issue_tags=_facet_list(row, "issue_tags"),
        mvp_relevance=row.facets.get("mvp_relevance") if row.facets else None,
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
    source = _usable_facts(row.facts)
    if not source:
        material_summary = _material_fact_summary(row.case_name, row.material_facts)
        if material_summary:
            return material_summary
        return f"이 판례는 {row.case_name} 사건입니다. 사실관계 요약은 아직 준비 중입니다."
    compact = " ".join(str(source).split())
    if len(compact) <= 120:
        return compact
    return f"{compact[:117]}..."


def _usable_facts(value: str | None) -> str | None:
    compact = " ".join(str(value or "").split())
    if not compact:
        return None
    order_like_markers = (
        "항소심에서",
        "제1심판결",
        "상고를 기각",
        "항소를 기각",
        "청구를 기각",
        "소송비용",
        "피고는 원고",
        "원고의 청구",
    )
    if any(marker in compact for marker in order_like_markers):
        return None
    return compact


def _material_fact_summary(case_name: str, material_facts: dict[str, object]) -> str | None:
    if not material_facts:
        return None

    event_type = _material_value(material_facts, "event_type")
    claim_type = _material_value(material_facts, "claim_type")
    legal_domain = _material_value(material_facts, "legal_domain")
    key_disputed_fact = _material_value(material_facts, "key_disputed_fact")
    outcome = _material_value(material_facts, "outcome_disposition")

    issue_labels = []
    if material_facts.get("negligence_dispute") is True:
        issue_labels.append("과실")
    if material_facts.get("causation_dispute") is True:
        issue_labels.append("인과관계")
    if material_facts.get("damage_scope_dispute") is True:
        issue_labels.append("손해 범위")
    if material_facts.get("evidence_issue") is True:
        issue_labels.append("증거")
    if key_disputed_fact and key_disputed_fact not in issue_labels:
        issue_labels.append(key_disputed_fact)

    subject = event_type or claim_type or legal_domain or case_name
    parts = [f"{subject} 관련 사건입니다."]
    if issue_labels:
        parts.append(f"주요 쟁점은 {', '.join(issue_labels[:3])}입니다.")
    if outcome:
        parts.append(f"판결 결과는 {outcome}입니다.")
    return " ".join(parts)


def _material_value(material_facts: dict[str, object], key: str) -> str | None:
    value = material_facts.get(key)
    if value in (None, "", False, "unknown"):
        return None
    return str(value)


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


def _facet_string(row: CaseSearchRow, key: str) -> str | None:
    value = row.facets.get(key) if row.facets else None
    return value if isinstance(value, str) else None


def _facet_list(row: CaseSearchRow, key: str) -> list[str]:
    value = row.facets.get(key) if row.facets else None
    return value if isinstance(value, list) else []


def _parse_intent(query: str) -> ParsedIntent:
    compact = " ".join(query.split())
    keywords = _keywords(compact)
    inferred_articles = _infer_articles(compact)
    legal_domain = _infer_domain(compact)
    case_type = "civil" if legal_domain else None
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
    for token in _expanded_legal_terms(query):
        if token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result[:12]


def _infer_articles(query: str) -> list[str]:
    inferred: list[str] = []
    rules = [
        (["750", "\uc81c750", "\ubd88\ubc95\ud589\uc704", "\uc190\ud574\ubc30\uc0c1"], "민법_제750조"),
        (["751", "\uc81c751", "\uc704\uc790\ub8cc", "\uba85\uc608"], "민법_제751조"),
        (["756", "\uc81c756", "사용자책임", "사용자 책임", "회사 직원", "업무 중"], "민법_제756조"),
        (["760", "\uc81c760", "공동불법행위", "공동 불법행위", "여러 사람"], "민법_제760조"),
        (["393", "\uc81c393", "통상손해", "특별손해", "배상 범위", "손해배상 범위"], "민법_제393조"),
        (["396", "\uc81c396", "\uacfc\uc2e4\uc0c1\uacc4", "\uacfc\uc2e4", "잘못", "감액", "줄어든"], "민법_제396조"),
        (["766", "\uc81c766", "소멸시효", "손해배상청구권"], "민법_제766조"),
    ]
    lowered = query.lower()
    for needles, article in rules:
        if any(needle in lowered for needle in needles):
            inferred.append(article)
    return inferred


def _expanded_legal_terms(query: str) -> list[str]:
    lowered = query.lower()
    expansions: list[str] = []
    if _contains_any(lowered, ["잘못", "감액", "줄어든", "줄어"]):
        expansions.extend(["과실", "과실상계", "배상액"])
    if _contains_any(lowered, ["회사 직원", "업무 중", "사용자 책임"]):
        expansions.extend(["사용자책임", "사용자", "직원", "업무"])
    if _contains_any(lowered, ["여러 사람", "함께", "공동"]):
        expansions.extend(["공동불법행위", "공동", "불법행위"])
    if _contains_any(lowered, ["통상손해", "특별손해", "배상 범위"]):
        expansions.extend(["손해배상범위", "통상손해", "특별손해"])
    if _contains_any(lowered, ["소멸시효", "청구권"]):
        expansions.extend(["손해배상청구권", "소멸시효"])
    return expansions


def _infer_domain(query: str) -> str | None:
    rules = [
        ("damages", ["damage", "damages", "손해", "배상", "불법행위", "교통사고", "위자료"]),
        ("unjust_enrichment", ["unjust enrichment", "restitution", "부당이득"]),
        ("lease", ["lease", "deposit", "eviction", "임대차", "보증금", "건물명도", "토지인도"]),
        ("labor", ["labor", "employment", "wage", "dismissal", "임금", "근로자지위", "해고", "퇴직금", "파견근로"]),
        ("inheritance", ["inheritance", "estate", "will", "상속", "유류분", "유언"]),
        ("tax", ["tax", "acquisition tax", "취득세", "조세", "부가가치세", "법인세", "소득세"]),
        ("property", ["property", "ownership", "mortgage", "소유권", "근저당", "말소등기", "이전등기", "점유"]),
        ("ip", ["patent", "trademark", "copyright", "특허", "실용신안", "상표", "저작권", "지식재산"]),
        ("contract", ["contract", "payment", "sale price", "약정금", "매매대금", "물품대금", "공사대금", "채무불이행"]),
        ("insurance", ["insurance", "subrogation", "보험금", "보험자", "구상금"]),
        ("family", ["divorce", "custody", "이혼", "재산분할", "친권", "양육"]),
    ]
    lowered = query.lower()
    for domain, terms in rules:
        if any(term.lower() in lowered for term in terms):
            return domain
    return None


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
                row.facets.get("primary_domain") if row.facets else "",
                " ".join(row.facets.get("secondary_domains", [])) if row.facets else "",
                " ".join(row.facets.get("issue_tags", [])) if row.facets else "",
                row.facts,
                row.conclusion,
                " ".join(row.cited_articles),
                " ".join(str(item) for item in row.outcome.values()),
            ]
        ).lower()
        text_terms = set(re.findall(r"[0-9A-Za-z가-힣_]+", text))
        keyword_score = _overlap(query_terms, text_terms)
        article_score = _overlap(set(intent.inferred_articles), set(row.cited_articles))
        primary_domain = str(row.facets.get("primary_domain", "")) if row.facets else ""
        secondary_domains = {
            str(value)
            for value in row.facets.get("secondary_domains", [])
            if isinstance(value, str)
        } if row.facets else set()
        domain_score = _domain_score(intent.legal_domain, primary_domain, secondary_domains)
        fuzzy_score = 1.0 if query.lower() in text else 0.0
        embedding_score = embedding_scores.get(row.case_id, 0.0)
        damages_relevance_score = {
            "mvp_relevant": 1.0,
            "weakly_related": 0.45,
            "out_of_scope": -0.5,
        }.get(str(row.facets.get("mvp_relevance", "")), 0.0) if intent.legal_domain == "damages" else 0.0
        score = min(
            1.0,
            (keyword_score * 0.29)
            + (article_score * 0.2)
            + (domain_score * 0.24)
            + (fuzzy_score * 0.04)
            + (embedding_score * 0.16)
            + (row.confidence_score * 0.10)
            + (damages_relevance_score * 0.03),
        )
        if score > 0 or not query_terms:
            ranked.append((row, round(score, 3)))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def _domain_score(
    expected_domain: str | None,
    primary_domain: str,
    secondary_domains: set[str],
) -> float:
    if not expected_domain:
        return 0.0
    if primary_domain == expected_domain:
        return 1.0
    if expected_domain in secondary_domains:
        return 0.25
    return 0.0


def _overlap(left: set[str], right: set[str]) -> float:
    if not left:
        return 0.0
    return len(left & right) / len(left)


def _contains_any(value: str, needles: list[str]) -> bool:
    lowered = value.lower()
    return any(needle in lowered for needle in needles)
