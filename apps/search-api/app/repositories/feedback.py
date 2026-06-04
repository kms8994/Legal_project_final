from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass(frozen=True)
class FeedbackInput:
    query_id: str | None
    base_case_id: str | None
    compare_case_id: str | None
    label: str
    reason: str | None
    comment: str | None
    user_id: str | None


class FeedbackRepository(Protocol):
    def save(self, feedback: FeedbackInput) -> str:
        ...


class PostgresFeedbackRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def save(self, feedback: FeedbackInput) -> str:
        row = self.connection.execute(
            text(
                """
                insert into comparison_feedbacks (
                  user_id,
                  query_id,
                  base_case_id,
                  compare_case_id,
                  label,
                  reason,
                  comment
                )
                values (
                  :user_id,
                  cast(:query_id as uuid),
                  cast(:base_case_id as uuid),
                  cast(:compare_case_id as uuid),
                  :label,
                  :reason,
                  :comment
                )
                returning id::text as feedback_id
                """
            ),
            {
                "user_id": feedback.user_id,
                "query_id": feedback.query_id,
                "base_case_id": feedback.base_case_id,
                "compare_case_id": feedback.compare_case_id,
                "label": feedback.label,
                "reason": feedback.reason,
                "comment": feedback.comment,
            },
        ).mappings().one()
        self.connection.commit()
        return row["feedback_id"]
