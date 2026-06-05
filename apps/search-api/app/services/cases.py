from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.repositories.cases import CaseDetailRepository, CaseStructureRecord, CompareCandidateRecord
from app.services.gemini import GeminiGenerationError, generate_case_summary
from pipelines.common.embedding import embedding_model_name
from app.schemas.cases import (
    CaseDetailResponse,
    CaseMeta,
    CaseRagSummary,
    CaseRagSummaryResponse,
    CaseStructure,
    CompareBaseCase,
    CompareCandidate,
    CompareCandidateScores,
    CompareCandidatesResponse,
    CompareAnalysis,
    CompareCaseSummary,
    CompareEvidenceLinks,
    CompareResponse,
    EvidenceIdPair,
    EvidenceLink,
    EvidenceLinkedClaim,
    EvidenceParagraph,
    MaterialDifference,
    RankingPolicy,
    RelaxationAttempt,
    RagSummarySection,
    TurningPoint,
)


class CaseNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class CaseDetailService:
    repository: CaseDetailRepository

    def get_detail(self, case_id: str) -> CaseDetailResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)

        structure = self.repository.get_structure(case_id)
        paragraphs = self.repository.list_paragraphs(case_id)

        return CaseDetailResponse(
            case=CaseMeta(
                case_id=case.case_id,
                external_id=case.external_id,
                case_no=case.case_no,
                court_name=case.court_name,
                court_level=case.court_level,
                decision_date=case.decision_date,
                case_name=case.case_name,
                case_type=case.case_type,
                legal_domain=case.legal_domain,
                source_url=case.source_url,
                collected_at=case.collected_at,
            ),
            structure=CaseStructure(
                facts=structure.facts if structure else None,
                legal_issue=structure.legal_issue if structure else None,
                court_reasoning=structure.court_reasoning if structure else None,
                conclusion=structure.conclusion if structure else None,
                material_facts=structure.material_facts if structure else {},
                outcome=structure.outcome if structure else {},
                cited_articles=structure.cited_articles if structure else [],
                facets=structure.facets if structure else {},
                evidence_spans=structure.evidence_spans if structure else {},
                confidence_score=structure.confidence_score if structure else 0.0,
                review_status=structure.review_status if structure else "pending",
            ),
            paragraphs=[
                EvidenceParagraph(
                    evidence_id=paragraph.paragraph_id,
                    paragraph_id=paragraph.paragraph_id,
                    section_type=paragraph.section_type,
                    paragraph_order=paragraph.paragraph_order,
                    text=paragraph.text,
                    char_start=paragraph.char_start,
                    char_end=paragraph.char_end,
                )
                for paragraph in paragraphs
            ],
        )

    def get_rag_summary(self, case_id: str) -> CaseRagSummaryResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)

        structure = self.repository.get_structure(case_id) or _empty_structure()
        paragraphs = self.repository.list_paragraphs(case_id)
        evidence_ids = _evidence_ids(structure.evidence_spans)
        evidence_links = _evidence_links(paragraphs, evidence_ids)
        if not evidence_links:
            evidence_links = [
                EvidenceLink(
                    evidence_id=paragraph.paragraph_id,
                    section_type=paragraph.section_type,
                    text=paragraph.text,
                )
                for paragraph in paragraphs[:5]
            ]

        local_summary = CaseRagSummary(
            facts=_summary_section(
                "사실관계",
                structure.facts or _case_card_summary(
                    None,
                    case.case_name,
                    structure.material_facts,
                ),
                evidence_links,
                preferred_sections={"facts", "summary", "unknown"},
                fallback="요약할 사실관계 데이터가 아직 충분하지 않습니다.",
            ),
            issue=_summary_section(
                "법적 쟁점",
                structure.legal_issue,
                evidence_links,
                preferred_sections={"issue", "reasoning", "facts"},
                fallback="법적 쟁점이 아직 명확히 구조화되지 않았습니다.",
            ),
            reasoning=_summary_section(
                "법원의 판단",
                structure.court_reasoning,
                evidence_links,
                preferred_sections={"reasoning", "holding", "unknown"},
                fallback="법원의 판단 이유가 아직 명확히 구조화되지 않았습니다.",
            ),
            outcome=_summary_section(
                "결론",
                structure.conclusion or _outcome_text(structure.outcome),
                evidence_links,
                preferred_sections={"order", "outcome", "conclusion", "unknown"},
                fallback="구조화된 결론 데이터가 아직 없습니다.",
            ),
            generated_by="local_grounded_extractive_rag",
            fallback_used=True,
            fallback_reason="GEMINI_API_KEY_NOT_CONFIGURED",
        )
        summary = _gemini_summary_or_fallback(
            case_name=case.case_name,
            case_no=case.case_no,
            structure=structure,
            evidence_links=evidence_links,
            fallback=local_summary,
        )

        return CaseRagSummaryResponse(
            case=CaseMeta(
                case_id=case.case_id,
                external_id=case.external_id,
                case_no=case.case_no,
                court_name=case.court_name,
                court_level=case.court_level,
                decision_date=case.decision_date,
                case_name=case.case_name,
                case_type=case.case_type,
                legal_domain=case.legal_domain,
                source_url=case.source_url,
                collected_at=case.collected_at,
            ),
            summary=summary,
            evidence_links=evidence_links,
            disclaimer=(
                "이 요약은 연결된 근거 문단과 구조화된 판례 필드만 바탕으로 생성되었습니다. "
                "실제 활용 전 공식 원문을 함께 확인하세요."
            ),
        )

    def get_compare_candidates(
        self,
        case_id: str,
        *,
        limit: int,
        require_outcome_difference: bool,
    ) -> CompareCandidatesResponse:
        case = self.repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(case_id)

        structure = self.repository.get_structure(case_id)
        if structure is None:
            structure = _empty_structure()

        effective_model = embedding_model_name(
            provider=settings.embedding_provider,
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )
        embedding_scores = self.repository.embedding_similarities_for_case(case_id, effective_model)
        candidates = [
            _to_candidate(structure, row, embedding_score=embedding_scores.get(row.case_id))
            for row in self.repository.list_compare_candidates(case_id)
        ]
        if require_outcome_difference:
            candidates = [
                candidate
                for candidate in candidates
                if candidate.scores.outcome_difference > 0
            ]

        candidates.sort(key=lambda candidate: candidate.scores.final_score, reverse=True)
        limited_candidates = candidates[:limit]
        relaxation_attempts = []
        if not limited_candidates and require_outcome_difference:
            relaxation_attempts.append(
                RelaxationAttempt(
                    level=1,
                    description="Relaxed outcome difference requirement.",
                    result_count=0,
                )
            )

        return CompareCandidatesResponse(
            base_case=CompareBaseCase(
                case_id=case.case_id,
                case_no=case.case_no,
                summary_card=_case_card_summary(
                    structure.facts,
                    case.case_name,
                    structure.material_facts,
                ),
                material_facts=structure.material_facts,
            ),
            ranking_policy=RankingPolicy(
                policy_name="Set B: balanced structured fallback",
                outcome_difference_weight=0.03,
            ),
            candidates=limited_candidates,
            relaxation_attempts=relaxation_attempts,
        )

    def compare_cases(self, base_case_id: str, compare_case_id: str) -> CompareResponse:
        base_case = self.repository.get_case(base_case_id)
        compare_case = self.repository.get_case(compare_case_id)
        if base_case is None:
            raise CaseNotFoundError(base_case_id)
        if compare_case is None:
            raise CaseNotFoundError(compare_case_id)

        base_structure = self.repository.get_structure(base_case_id) or _empty_structure()
        compare_structure = self.repository.get_structure(compare_case_id) or _empty_structure()
        base_paragraphs = self.repository.list_paragraphs(base_case_id)
        compare_paragraphs = self.repository.list_paragraphs(compare_case_id)
        base_evidence_ids = _evidence_ids(base_structure.evidence_spans)
        compare_evidence_ids = _evidence_ids(compare_structure.evidence_spans)

        return CompareResponse(
            base=CompareCaseSummary(
                case_id=base_case.case_id,
                case_no=base_case.case_no,
                court_name=base_case.court_name,
                decision_date=base_case.decision_date,
                outcome=base_structure.outcome,
            ),
            compare=CompareCaseSummary(
                case_id=compare_case.case_id,
                case_no=compare_case.case_no,
                court_name=compare_case.court_name,
                decision_date=compare_case.decision_date,
                outcome=compare_structure.outcome,
            ),
            analysis=CompareAnalysis(
                common_points=_common_points(
                    base_structure,
                    compare_structure,
                    base_evidence_ids,
                    compare_evidence_ids,
                ),
                material_differences=_material_differences(
                    base_structure,
                    compare_structure,
                    base_evidence_ids,
                    compare_evidence_ids,
                ),
                turning_points=_analysis_turning_points(
                    base_structure,
                    compare_structure,
                    base_evidence_ids,
                    compare_evidence_ids,
                ),
                result_difference=_outcome_summary(
                    base_structure.outcome,
                    compare_structure.outcome,
                ),
                generated_by="structured_fallback",
                fallback_used=True,
                fallback_reason="LLM_NOT_CONFIGURED",
            ),
            evidence_links=CompareEvidenceLinks(
                base=_evidence_links(base_paragraphs, base_evidence_ids),
                compare=_evidence_links(compare_paragraphs, compare_evidence_ids),
            ),
            disclaimer=(
                "CaseLens comparison analysis is for reference only and does not replace "
                "legal judgment or review of the official source text."
            ),
        )


def _empty_structure() -> CaseStructureRecord:
    return CaseStructureRecord(
        facts=None,
        legal_issue=None,
        court_reasoning=None,
        conclusion=None,
        material_facts={},
        outcome={},
        cited_articles=[],
        facets={},
        evidence_spans={},
        confidence_score=0.0,
        review_status="pending",
    )


def _to_candidate(
    base: CaseStructureRecord,
    row: CompareCandidateRecord,
    *,
    embedding_score: float | None = None,
) -> CompareCandidate:
    material_fact_match = _mapping_similarity(base.material_facts, row.material_facts)
    domain_match_score = _domain_match_score(base, row)
    issue_tag_overlap = _issue_tag_overlap(base.facets, row.facets)
    facet_match_score = (domain_match_score * 0.6) + (issue_tag_overlap * 0.4)
    statute_overlap = _list_overlap(base.cited_articles, row.cited_articles)
    issue_similarity = _token_similarity(base.legal_issue, row.legal_issue)
    facts_similarity = embedding_score if embedding_score is not None else _token_similarity(base.facts, row.facts)
    event_structure_match = (material_fact_match + facts_similarity) / 2
    outcome_difference = 1.0 if _outcome_differs(base.outcome, row.outcome) else 0.0
    match_reasons = _match_reasons(
        base,
        row,
        material_fact_match=material_fact_match,
        statute_overlap=statute_overlap,
        domain_match_score=domain_match_score,
        issue_tag_overlap=issue_tag_overlap,
        issue_similarity=issue_similarity,
    )
    caution_reasons = _caution_reasons(
        base,
        row,
        material_fact_match=material_fact_match,
        statute_overlap=statute_overlap,
        domain_match_score=domain_match_score,
        issue_tag_overlap=issue_tag_overlap,
    )
    final_score = _clamp(
        (material_fact_match * 0.30)
        + (event_structure_match * 0.12)
        + (issue_similarity * 0.12)
        + (statute_overlap * 0.10)
        + (domain_match_score * 0.15)
        + (issue_tag_overlap * 0.20)
        + (facet_match_score * 0.03)
        + ((embedding_score or 0.0) * 0.02)
        + (outcome_difference * 0.02)
        + (_clamp(row.confidence_score) * 0.01)
        - _compare_candidate_penalty(
            base,
            row,
            material_fact_match=material_fact_match,
            issue_tag_overlap=issue_tag_overlap,
        )
    )

    return CompareCandidate(
        case_id=row.case_id,
        case_no=row.case_no,
        court_name=row.court_name,
        decision_date=row.decision_date,
        case_name=row.case_name,
        summary_card=_case_card_summary(row.facts, row.case_name, row.material_facts),
        scores=CompareCandidateScores(
            facts_vector_similarity=round(facts_similarity, 3),
            material_fact_match=round(material_fact_match, 3),
            event_structure_match=round(event_structure_match, 3),
            issue_similarity=round(issue_similarity, 3),
            statute_overlap=round(statute_overlap, 3),
            domain_match_score=round(domain_match_score, 3),
            issue_tag_overlap=round(issue_tag_overlap, 3),
            facet_match_score=round(facet_match_score, 3),
            outcome_difference=round(outcome_difference, 3),
            final_score=round(final_score, 3),
        ),
        match_reasons=match_reasons,
        caution_reasons=caution_reasons,
        common_facts=_common_material_facts(base.material_facts, row.material_facts),
        possible_turning_points=_turning_points(base.material_facts, row.material_facts),
        outcome_difference_summary=_outcome_summary(base.outcome, row.outcome),
        relaxation_level=0,
        evidence_ids=_evidence_ids(row.evidence_spans),
    )


def _summary(value: str | None) -> str:
    compact = " ".join(str(value or "").split())
    if len(compact) <= 120:
        return compact
    return f"{compact[:117]}..."


def _case_card_summary(
    facts: str | None,
    case_name: str,
    material_facts: dict[str, Any] | None = None,
) -> str:
    source = _usable_facts(facts)
    if not source:
        material_summary = _material_fact_summary(case_name, material_facts or {})
        if material_summary:
            return material_summary
        return f"이 판례는 {case_name} 사건입니다. 사실관계 요약은 아직 준비 중입니다."
    return _summary(source)


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


def _material_fact_summary(case_name: str, material_facts: dict[str, Any]) -> str | None:
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


def _material_value(material_facts: dict[str, Any], key: str) -> str | None:
    value = material_facts.get(key)
    if value in (None, "", False, "unknown"):
        return None
    return str(value)


def _summary_section(
    title: str,
    structured_text: str | None,
    evidence_links: list[EvidenceLink],
    *,
    preferred_sections: set[str],
    fallback: str,
) -> RagSummarySection:
    selected = _select_evidence(evidence_links, preferred_sections)
    source_text = structured_text or " ".join(link.text for link in selected)
    summary_text = _compact_summary(source_text, fallback=fallback)
    if selected and structured_text:
        evidence_text = _compact_summary(" ".join(link.text for link in selected), fallback="")
        if evidence_text and evidence_text not in summary_text:
            summary_text = f"{summary_text} 근거 문단은 다음 내용을 포함합니다: {evidence_text}"

    return RagSummarySection(
        title=title,
        text=summary_text,
        evidence_ids=[link.evidence_id for link in selected[:3]],
    )


def _gemini_summary_or_fallback(
    *,
    case_name: str,
    case_no: str,
    structure: CaseStructureRecord,
    evidence_links: list[EvidenceLink],
    fallback: CaseRagSummary,
) -> CaseRagSummary:
    if not settings.gemini_api_key:
        return fallback

    try:
        generated = generate_case_summary(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            case_name=case_name,
            case_no=case_no,
            structured_fields={
                "facts": structure.facts,
                "legal_issue": structure.legal_issue,
                "court_reasoning": structure.court_reasoning,
                "conclusion": structure.conclusion,
                "material_facts": structure.material_facts,
                "outcome": structure.outcome,
                "cited_articles": structure.cited_articles,
            },
            evidence_links=[
                {
                    "evidence_id": link.evidence_id,
                    "section_type": link.section_type,
                    "text": link.text,
                }
                for link in evidence_links
            ],
        )
    except GeminiGenerationError as exc:
        fallback.fallback_reason = f"GEMINI_GENERATION_FAILED: {_summary(str(exc))}"
        return fallback

    return CaseRagSummary(
        facts=RagSummarySection(
            title="사실관계",
            text=generated.get("facts") or fallback.facts.text,
            evidence_ids=fallback.facts.evidence_ids,
        ),
        issue=RagSummarySection(
            title="법적 쟁점",
            text=generated.get("issue") or fallback.issue.text,
            evidence_ids=fallback.issue.evidence_ids,
        ),
        reasoning=RagSummarySection(
            title="법원의 판단",
            text=generated.get("reasoning") or fallback.reasoning.text,
            evidence_ids=fallback.reasoning.evidence_ids,
        ),
        outcome=RagSummarySection(
            title="결론",
            text=generated.get("outcome") or fallback.outcome.text,
            evidence_ids=fallback.outcome.evidence_ids,
        ),
        generated_by=settings.gemini_model,
        fallback_used=False,
        fallback_reason=None,
    )


def _select_evidence(
    evidence_links: list[EvidenceLink],
    preferred_sections: set[str],
) -> list[EvidenceLink]:
    preferred = [
        link
        for link in evidence_links
        if link.section_type.lower() in preferred_sections
    ]
    return (preferred or evidence_links)[:3]


def _compact_summary(value: str | None, *, fallback: str) -> str:
    compact = " ".join(str(value or "").split())
    if not compact:
        return fallback
    sentences = [
        sentence.strip()
        for sentence in compact.replace("다.", "다.|").replace(".", ".|").split("|")
        if sentence.strip()
    ]
    summary = " ".join(sentences[:2]) if sentences else compact
    if len(summary) <= 260:
        return summary
    return f"{summary[:257]}..."


def _outcome_text(outcome: dict[str, Any]) -> str | None:
    if not outcome:
        return None
    parts = [
        f"{key}: {value}"
        for key, value in outcome.items()
        if value not in (None, "")
    ]
    return "; ".join(parts) if parts else None


def _mapping_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    matched = 0
    for key in keys:
        if key in left and key in right and left[key] == right[key]:
            matched += 1
    return matched / len(keys)


def _domain_match_score(base: CaseStructureRecord, row: CompareCandidateRecord) -> float:
    base_primary, base_secondary = _domain_values(base.facets)
    row_primary, row_secondary = _domain_values(row.facets)
    if not base_primary or not row_primary:
        return 0.0
    if base_primary == row_primary:
        return 1.0 if base_primary != "general" else 0.6
    if base_primary in row_secondary or row_primary in base_secondary:
        return 0.35
    return 0.0


def _match_reasons(
    base: CaseStructureRecord,
    row: CompareCandidateRecord,
    *,
    material_fact_match: float,
    statute_overlap: float,
    domain_match_score: float,
    issue_tag_overlap: float,
    issue_similarity: float,
) -> list[str]:
    base_domain, _ = _domain_values(base.facets)
    row_domain, _ = _domain_values(row.facets)
    reasons: list[str] = []
    if domain_match_score >= 1.0 and base_domain:
        reasons.append(f"same primary legal domain: {base_domain}")
    elif domain_match_score > 0 and base_domain and row_domain:
        reasons.append(f"related legal domains: {base_domain} vs {row_domain}")
    shared_tags = sorted(set(_string_list(base.facets.get("issue_tags"))) & set(_string_list(row.facets.get("issue_tags"))))
    if shared_tags:
        reasons.append(f"shared issue tags: {', '.join(shared_tags[:3])}")
    if material_fact_match >= 0.5:
        reasons.append("similar material fact structure")
    if statute_overlap > 0:
        shared = sorted(set(base.cited_articles) & set(row.cited_articles))
        reasons.append(f"overlapping cited articles: {', '.join(shared[:3])}")
    if issue_similarity >= 0.5:
        reasons.append("similar legal issue text")
    return reasons[:5]


def _caution_reasons(
    base: CaseStructureRecord,
    row: CompareCandidateRecord,
    *,
    material_fact_match: float,
    statute_overlap: float,
    domain_match_score: float,
    issue_tag_overlap: float,
) -> list[str]:
    base_domain, _ = _domain_values(base.facets)
    row_domain, _ = _domain_values(row.facets)
    cautions: list[str] = []
    if base_domain and row_domain and base_domain != row_domain and domain_match_score < 1.0:
        cautions.append(f"different primary legal domains: {base_domain} vs {row_domain}")
    if issue_tag_overlap == 0:
        cautions.append("no shared issue tags")
    if material_fact_match < 0.3:
        cautions.append("low material fact match")
    if statute_overlap == 0 and base.cited_articles and row.cited_articles:
        cautions.append("no overlapping cited articles")
    return cautions[:4]


def _compare_candidate_penalty(
    base: CaseStructureRecord,
    row: CompareCandidateRecord,
    *,
    material_fact_match: float,
    issue_tag_overlap: float,
) -> float:
    penalty = 0.0
    base_tags = _string_list(base.facets.get("issue_tags"))
    row_tags = _string_list(row.facets.get("issue_tags"))
    if base_tags and not row_tags:
        penalty += 0.08
    elif base_tags and row_tags and issue_tag_overlap == 0:
        penalty += 0.06
    if material_fact_match < 0.3:
        penalty += 0.08
    return penalty


def _domain_values(facets: dict[str, Any]) -> tuple[str | None, set[str]]:
    primary = _string_value(facets.get("primary_domain") or facets.get("legal_domain"))
    secondary = {
        value
        for value in _string_list(facets.get("secondary_domains"))
        if value != primary
    }
    return primary, secondary


def _issue_tag_overlap(left: dict[str, Any], right: dict[str, Any]) -> float:
    return _list_overlap(_string_list(left.get("issue_tags")), _string_list(right.get("issue_tags")))


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _list_overlap(left: list[str], right: list[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def _token_similarity(left: str | None, right: str | None) -> float:
    left_tokens = set(str(left or "").lower().split())
    right_tokens = set(str(right or "").lower().split())
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _outcome_differs(left: dict[str, Any], right: dict[str, Any]) -> bool:
    for key in ("direction", "disposition", "key_factor", "ratio_or_percentage"):
        if left.get(key) and right.get(key) and left.get(key) != right.get(key):
            return True
    return False


def _common_material_facts(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    return [
        f"{key}: {left[key]}"
        for key in sorted(set(left) & set(right))
        if left[key] == right[key]
    ][:5]


def _turning_points(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    return [
        f"{key}: {left.get(key)} vs {right.get(key)}"
        for key in sorted(set(left) & set(right))
        if left.get(key) != right.get(key)
    ][:5]


def _common_points(
    base: CaseStructureRecord,
    compare: CaseStructureRecord,
    base_evidence_ids: list[str],
    compare_evidence_ids: list[str],
) -> list[EvidenceLinkedClaim]:
    base_domain, _ = _domain_values(base.facets)
    compare_domain, _ = _domain_values(compare.facets)
    claims = [
        EvidenceLinkedClaim(
            text=f"Both cases share material fact `{key}` with value `{base.material_facts[key]}`.",
            evidence_ids=EvidenceIdPair(base=base_evidence_ids[:2], compare=compare_evidence_ids[:2]),
        )
        for key in sorted(set(base.material_facts) & set(compare.material_facts))
        if base.material_facts[key] == compare.material_facts[key]
    ]
    if _list_overlap(base.cited_articles, compare.cited_articles) > 0:
        shared = sorted(set(base.cited_articles) & set(compare.cited_articles))
        claims.append(
            EvidenceLinkedClaim(
                text=f"Both cases cite overlapping statutes: {', '.join(shared)}.",
                evidence_ids=EvidenceIdPair(base=base_evidence_ids[:2], compare=compare_evidence_ids[:2]),
            )
        )
    if base_domain and base_domain == compare_domain:
        claims.append(
            EvidenceLinkedClaim(
                text=f"Both cases are classified under legal domain `{base_domain}`.",
                evidence_ids=EvidenceIdPair(base=base_evidence_ids[:2], compare=compare_evidence_ids[:2]),
            )
        )
    shared_tags = sorted(set(_string_list(base.facets.get("issue_tags"))) & set(_string_list(compare.facets.get("issue_tags"))))
    if shared_tags:
        claims.append(
            EvidenceLinkedClaim(
                text=f"Both cases share issue tags: {', '.join(shared_tags)}.",
                evidence_ids=EvidenceIdPair(base=base_evidence_ids[:2], compare=compare_evidence_ids[:2]),
            )
        )
    return claims[:5]


def _material_differences(
    base: CaseStructureRecord,
    compare: CaseStructureRecord,
    base_evidence_ids: list[str],
    compare_evidence_ids: list[str],
) -> list[MaterialDifference]:
    base_domain, _ = _domain_values(base.facets)
    compare_domain, _ = _domain_values(compare.facets)
    differences = [
        MaterialDifference(
            factor=key,
            base=str(base.material_facts.get(key)),
            compare=str(compare.material_facts.get(key)),
            meaning=(
                f"The `{key}` difference may affect how close the candidate is to the base case."
            ),
            evidence_ids=EvidenceIdPair(base=base_evidence_ids[:2], compare=compare_evidence_ids[:2]),
        )
        for key in sorted(set(base.material_facts) & set(compare.material_facts))
        if base.material_facts.get(key) != compare.material_facts.get(key)
    ]
    if base_domain and compare_domain and base_domain != compare_domain:
        differences.append(
            MaterialDifference(
                factor="primary_domain",
                base=base_domain,
                compare=compare_domain,
                meaning="Different legal domains make this candidate weaker for direct comparison.",
                evidence_ids=EvidenceIdPair(base=base_evidence_ids[:2], compare=compare_evidence_ids[:2]),
            )
        )
    return differences[:5]


def _analysis_turning_points(
    base: CaseStructureRecord,
    compare: CaseStructureRecord,
    base_evidence_ids: list[str],
    compare_evidence_ids: list[str],
) -> list[TurningPoint]:
    points = [
        TurningPoint(
            title=difference.factor,
            explanation=(
                f"Base has `{difference.base}`, while compare has `{difference.compare}`."
            ),
            evidence_ids=difference.evidence_ids,
        )
        for difference in _material_differences(
            base,
            compare,
            base_evidence_ids,
            compare_evidence_ids,
        )
    ]
    outcome = _outcome_summary(base.outcome, compare.outcome)
    if outcome != "No structured outcome difference was detected.":
        points.append(
            TurningPoint(
                title="Outcome",
                explanation=outcome,
                evidence_ids=EvidenceIdPair(base=base_evidence_ids[:2], compare=compare_evidence_ids[:2]),
            )
        )
    return points[:5]


def _outcome_summary(left: dict[str, Any], right: dict[str, Any]) -> str:
    differences = [
        f"{key}: {left.get(key)} vs {right.get(key)}"
        for key in ("direction", "disposition", "key_factor", "ratio_or_percentage")
        if left.get(key) and right.get(key) and left.get(key) != right.get(key)
    ]
    if not differences:
        return "No structured outcome difference was detected."
    return "; ".join(differences)


def _evidence_ids(evidence_spans: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for value in evidence_spans.values():
        ids.extend(_extract_evidence_ids(value))
    return ids[:5]


def _extract_evidence_ids(value: Any) -> list[str]:
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


def _evidence_links(paragraphs: list[Any], evidence_ids: list[str]) -> list[EvidenceLink]:
    allowed = set(evidence_ids)
    return [
        EvidenceLink(
            evidence_id=paragraph.paragraph_id,
            section_type=paragraph.section_type,
            text=paragraph.text,
        )
        for paragraph in paragraphs
        if paragraph.paragraph_id in allowed
    ][:5]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
