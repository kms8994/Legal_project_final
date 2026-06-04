from __future__ import annotations

from dataclasses import dataclass

from app.repositories.feedback import FeedbackInput, FeedbackRepository
from app.schemas.feedback import FeedbackRequest, FeedbackResponse


@dataclass(frozen=True)
class FeedbackService:
    repository: FeedbackRepository

    def save(self, request: FeedbackRequest) -> FeedbackResponse:
        feedback_id = self.repository.save(
            FeedbackInput(
                query_id=request.query_id,
                base_case_id=request.base_case_id,
                compare_case_id=request.compare_case_id,
                label=request.label,
                reason=request.reason,
                comment=request.comment,
                user_id=request.user_id,
            )
        )
        return FeedbackResponse(feedback_id=feedback_id)
