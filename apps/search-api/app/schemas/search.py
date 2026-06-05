from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class StatuteSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=50)
    sort: Literal["relevance", "decision_date"] = "relevance"


class StatuteQueryInfo(BaseModel):
    raw: str
    mode: Literal["statute"] = "statute"
    normalized_ref: str
    law_name: str
    article_no: str
    article_validated: bool


class Pagination(BaseModel):
    page: int
    size: int
    total: int
    has_next: bool


class SearchResultCard(BaseModel):
    case_id: str
    case_no: str
    court_name: str
    court_level: str | None = None
    decision_date: date | None = None
    case_name: str
    case_type: str | None = None
    legal_domain: str | None = None
    primary_domain: str | None = None
    secondary_domains: list[str] = Field(default_factory=list)
    issue_tags: list[str] = Field(default_factory=list)
    mvp_relevance: str | None = None
    summary_card: str
    outcome: dict[str, Any] = Field(default_factory=dict)
    cited_articles: list[str] = Field(default_factory=list)
    score: float
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_snippets: list["SearchEvidenceSnippet"] = Field(default_factory=list)
    source_url: str | None = None
    review_status: str
    confidence_score: float


class SearchEvidenceSnippet(BaseModel):
    evidence_id: str
    section_type: str
    paragraph_order: int
    text: str


class StatuteSearchResponse(BaseModel):
    query: StatuteQueryInfo
    pagination: Pagination
    results: list[SearchResultCard]


class NaturalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=50)


class ParsedIntent(BaseModel):
    case_type: str | None = None
    legal_domain: str | None = None
    keywords: list[str] = Field(default_factory=list)
    legal_issue: str | None = None
    inferred_articles: list[str] = Field(default_factory=list)
    inferred_articles_validated: bool
    facts_summary: str
    confidence: float
    needs_clarification: bool = False
    clarification_question: str | None = None


class NaturalSearchResponse(BaseModel):
    parsed_intent: ParsedIntent
    search_method: Literal["structured_fallback"] = "structured_fallback"
    pagination: Pagination
    results: list[SearchResultCard]


class ErrorResponse(BaseModel):
    code: str
    message: str
