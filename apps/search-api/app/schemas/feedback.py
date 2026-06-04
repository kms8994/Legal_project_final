from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


FeedbackLabel = Literal[
    "relevant",
    "not_relevant",
    "facts_not_similar",
    "material_fact_missed",
    "wrong_statute",
    "outcome_not_different",
    "summary_error",
    "source_needed",
]


class FeedbackRequest(BaseModel):
    query_id: str | None = None
    base_case_id: str | None = None
    compare_case_id: str | None = None
    label: FeedbackLabel
    reason: str | None = Field(default=None, max_length=500)
    comment: str | None = Field(default=None, max_length=2000)
    user_id: str | None = Field(default=None, max_length=200)


class FeedbackResponse(BaseModel):
    feedback_id: str
    status: Literal["saved"] = "saved"
