from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_connection
from app.repositories.cases import PostgresCaseDetailRepository
from app.schemas.cases import CompareRequest, CompareResponse
from app.schemas.search import ErrorResponse
from app.services.cases import CaseDetailService, CaseNotFoundError

router = APIRouter(prefix="/api/v1", tags=["compare"])


def get_compare_service(
    connection: Connection = Depends(get_connection),
) -> Iterator[CaseDetailService]:
    yield CaseDetailService(PostgresCaseDetailRepository(connection))


@router.post(
    "/compare",
    response_model=CompareResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def compare_cases(
    request: CompareRequest,
    service: CaseDetailService = Depends(get_compare_service),
) -> CompareResponse:
    try:
        return service.compare_cases(request.base_case_id, request.compare_case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CASE_NOT_FOUND",
                "message": f"Case was not found: {exc}",
            },
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "COMPARE_UNAVAILABLE",
                "message": "Compare analysis DB is unavailable.",
            },
        ) from exc
