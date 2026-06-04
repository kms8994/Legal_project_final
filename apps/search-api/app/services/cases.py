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
                "Facts",
                structure.facts,
                evidence_links,
                preferred_sections={"facts", "summary", "unknown"},
                fallback="The available evidence does not contain enough facts to summarize.",
            ),
            issue=_summary_section(
                "Issue",
                structure.legal_issue,
                evidence_links,
                preferred_sections={"issue", "reasoning", "facts"},
                fallback="The legal issue is not clearly structured yet.",
            ),
            reasoning=_summary_section(
                "Reasoning",
                structure.court_reasoning,
                evidence_links,
                preferred_sections={"reasoning", "holding", "unknown"},
                fallback="The court reasoning is not clearly structured yet.",
            ),
            outcome=_summary_section(
                "Outcome",
                structure.conclusion or _outcome_text(structure.outcome),
                evidence_links,
                preferred_sections={"order", "outcome", "conclusion", "unknown"},
                fallback="The structured outcome is not available yet.",
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
                "This summary is generated only from linked evidence paragraphs and structured "
                "case fields. Review the official source text before relying on it."
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
                summary_card=_summary(structure.conclusion or structure.facts or case.case_name),
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
    facet_match_score = _mapping_similarity(base.facets, row.facets)
    statute_overlap = _list_overlap(base.cited_articles, row.cited_articles)
    issue_similarity = _token_similarity(base.legal_issue, row.legal_issue)
    facts_similarity = embedding_score if embedding_score is not None else _token_similarity(base.facts, row.facts)
    event_structure_match = (material_fact_match + facts_similarity) / 2
    outcome_difference = 1.0 if _outcome_differs(base.outcome, row.outcome) else 0.0
    final_score = _clamp(
        (material_fact_match * 0.32)
        + (event_structure_match * 0.16)
        + (issue_similarity * 0.14)
        + (statute_overlap * 0.16)
        + (facet_match_score * 0.12)
        + ((embedding_score or 0.0) * 0.04)
        + (outcome_difference * 0.03)
        + (_clamp(row.confidence_score) * 0.03)
    )

    return CompareCandidate(
        case_id=row.case_id,
        case_no=row.case_no,
        court_name=row.court_name,
        decision_date=row.decision_date,
        case_name=row.case_name,
        summary_card=_summary(row.conclusion or row.facts or row.case_name),
        scores=CompareCandidateScores(
            facts_vector_similarity=round(facts_similarity, 3),
            material_fact_match=round(material_fact_match, 3),
            event_structure_match=round(event_structure_match, 3),
            issue_similarity=round(issue_similarity, 3),
            statute_overlap=round(statute_overlap, 3),
            facet_match_score=round(facet_match_score, 3),
            outcome_difference=round(outcome_difference, 3),
            final_score=round(final_score, 3),
        ),
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
            title="Facts",
            text=generated.get("facts") or fallback.facts.text,
            evidence_ids=fallback.facts.evidence_ids,
        ),
        issue=RagSummarySection(
            title="Issue",
            text=generated.get("issue") or fallback.issue.text,
            evidence_ids=fallback.issue.evidence_ids,
        ),
        reasoning=RagSummarySection(
            title="Reasoning",
            text=generated.get("reasoning") or fallback.reasoning.text,
            evidence_ids=fallback.reasoning.evidence_ids,
        ),
        outcome=RagSummarySection(
            title="Outcome",
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
    return claims[:5]


def _material_differences(
    base: CaseStructureRecord,
    compare: CaseStructureRecord,
    base_evidence_ids: list[str],
    compare_evidence_ids: list[str],
) -> list[MaterialDifference]:
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
