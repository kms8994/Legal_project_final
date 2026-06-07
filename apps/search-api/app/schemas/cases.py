from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class CaseMeta(BaseModel):
    case_id: str
    external_id: str
    case_no: str
    court_name: str
    court_level: str | None = None
    decision_date: date | None = None
    case_name: str
    case_type: str | None = None
    legal_domain: str | None = None
    source_url: str | None = None
    collected_at: datetime


class CaseStructure(BaseModel):
    facts: str | None = None
    legal_issue: str | None = None
    court_reasoning: str | None = None
    conclusion: str | None = None
    material_facts: dict[str, Any] = Field(default_factory=dict)
    outcome: dict[str, Any] = Field(default_factory=dict)
    cited_articles: list[str] = Field(default_factory=list)
    facets: dict[str, Any] = Field(default_factory=dict)
    evidence_spans: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    review_status: str = "pending"


class EvidenceParagraph(BaseModel):
    evidence_id: str
    paragraph_id: str
    section_type: str
    paragraph_order: int
    text: str
    char_start: int | None = None
    char_end: int | None = None


class CaseDetailResponse(BaseModel):
    case: CaseMeta
    structure: CaseStructure
    paragraphs: list[EvidenceParagraph]


class RagSummarySection(BaseModel):
    title: str
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class CaseRagSummary(BaseModel):
    facts: RagSummarySection
    issue: RagSummarySection
    reasoning: RagSummarySection
    outcome: RagSummarySection
    generated_by: str
    fallback_used: bool
    fallback_reason: str | None = None


class CaseRagSummaryResponse(BaseModel):
    case: CaseMeta
    summary: CaseRagSummary
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    disclaimer: str


class CompareBaseCase(BaseModel):
    case_id: str
    case_no: str
    summary_card: str
    material_facts: dict[str, Any] = Field(default_factory=dict)


class RankingPolicy(BaseModel):
    policy_name: str
    outcome_difference_weight: float


class CompareCandidateScores(BaseModel):
    facts_vector_similarity: float
    material_fact_match: float
    event_structure_match: float
    issue_similarity: float
    statute_overlap: float
    domain_match_score: float = 0.0
    issue_tag_overlap: float = 0.0
    facet_match_score: float
    outcome_difference: float
    final_score: float


class CompareCandidate(BaseModel):
    case_id: str
    case_no: str
    court_name: str
    decision_date: date | None = None
    case_name: str
    summary_card: str
    scores: CompareCandidateScores
    match_reasons: list[str] = Field(default_factory=list)
    caution_reasons: list[str] = Field(default_factory=list)
    common_facts: list[str] = Field(default_factory=list)
    possible_turning_points: list[str] = Field(default_factory=list)
    outcome_difference_summary: str
    relaxation_level: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    facts_summary: str | None = None
    reasoning_summary: str | None = None
    judgment_summary: str | None = None


class RelaxationAttempt(BaseModel):
    level: int
    description: str
    result_count: int


class CompareCandidatesResponse(BaseModel):
    base_case: CompareBaseCase
    ranking_policy: RankingPolicy
    candidates: list[CompareCandidate]
    relaxation_attempts: list[RelaxationAttempt] = Field(default_factory=list)


class CompareRequest(BaseModel):
    base_case_id: str
    compare_case_id: str


class CompareCaseSummary(BaseModel):
    case_id: str
    case_no: str
    court_name: str
    decision_date: date | None = None
    outcome: dict[str, Any] = Field(default_factory=dict)


class EvidenceIdPair(BaseModel):
    base: list[str] = Field(default_factory=list)
    compare: list[str] = Field(default_factory=list)


class EvidenceLinkedClaim(BaseModel):
    text: str
    evidence_ids: EvidenceIdPair


class MaterialDifference(BaseModel):
    factor: str
    base: str
    compare: str
    meaning: str
    evidence_ids: EvidenceIdPair


class TurningPoint(BaseModel):
    title: str
    explanation: str
    evidence_ids: EvidenceIdPair


class CompareAnalysis(BaseModel):
    common_points: list[EvidenceLinkedClaim] = Field(default_factory=list)
    material_differences: list[MaterialDifference] = Field(default_factory=list)
    turning_points: list[TurningPoint] = Field(default_factory=list)
    result_difference: str
    generated_by: str
    fallback_used: bool
    fallback_reason: str | None = None


class EvidenceLink(BaseModel):
    evidence_id: str
    section_type: str
    text: str


class CompareEvidenceLinks(BaseModel):
    base: list[EvidenceLink] = Field(default_factory=list)
    compare: list[EvidenceLink] = Field(default_factory=list)


class CompareResponse(BaseModel):
    base: CompareCaseSummary
    compare: CompareCaseSummary
    analysis: CompareAnalysis
    evidence_links: CompareEvidenceLinks
    disclaimer: str
