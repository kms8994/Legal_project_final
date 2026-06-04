from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_connection
from app.repositories.feedback import PostgresFeedbackRepository
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.search import ErrorResponse
from app.services.feedback import FeedbackService

router = APIRouter(prefix="/api/v1", tags=["feedback"])


def get_feedback_service(
    connection: Connection = Depends(get_connection),
) -> Iterator[FeedbackService]:
    yield FeedbackService(PostgresFeedbackRepository(connection))


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    responses={
        503: {"model": ErrorResponse},
    },
)
def save_feedback(
    request: FeedbackRequest,
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackResponse:
    try:
        return service.save(request)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "FEEDBACK_UNAVAILABLE",
                "message": "Feedback DB is unavailable.",
            },
        ) from exc
