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
    summary_card: str
    outcome: dict[str, Any] = Field(default_factory=dict)
    cited_articles: list[str] = Field(default_factory=list)
    score: float
    evidence_ids: list[str] = Field(default_factory=list)
    source_url: str | None = None
    review_status: str
    confidence_score: float


class StatuteSearchResponse(BaseModel):
    query: StatuteQueryInfo
    pagination: Pagination
    results: list[SearchResultCard]


class ErrorResponse(BaseModel):
    code: str
    message: str
