from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_connection
from app.repositories.cases import PostgresCaseDetailRepository
from app.schemas.cases import CaseDetailResponse, CaseRagSummaryResponse, CompareCandidatesResponse
from app.schemas.search import ErrorResponse
from app.services.cases import CaseDetailService, CaseNotFoundError

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def get_case_detail_service(
    connection: Connection = Depends(get_connection),
) -> Iterator[CaseDetailService]:
    yield CaseDetailService(PostgresCaseDetailRepository(connection))


@router.get(
    "/{case_id}",
    response_model=CaseDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_case_detail(
    case_id: UUID,
    service: CaseDetailService = Depends(get_case_detail_service),
) -> CaseDetailResponse:
    try:
        return service.get_detail(str(case_id))
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CASE_NOT_FOUND",
                "message": f"Case was not found: {case_id}",
            },
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CASE_DETAIL_UNAVAILABLE",
                "message": "Case detail DB is unavailable.",
            },
        ) from exc


@router.get(
    "/{case_id}/rag-summary",
    response_model=CaseRagSummaryResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_case_rag_summary(
    case_id: UUID,
    service: CaseDetailService = Depends(get_case_detail_service),
) -> CaseRagSummaryResponse:
    try:
        return service.get_rag_summary(str(case_id))
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CASE_NOT_FOUND",
                "message": f"Case was not found: {case_id}",
            },
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "RAG_SUMMARY_UNAVAILABLE",
                "message": "Case RAG summary DB is unavailable.",
            },
        ) from exc


@router.get(
    "/{case_id}/compare-candidates",
    response_model=CompareCandidatesResponse,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_compare_candidates(
    case_id: UUID,
    limit: int = 5,
    require_outcome_difference: bool = True,
    service: CaseDetailService = Depends(get_case_detail_service),
) -> CompareCandidatesResponse:
    safe_limit = max(1, min(limit, 20))
    try:
        return service.get_compare_candidates(
            str(case_id),
            limit=safe_limit,
            require_outcome_difference=require_outcome_difference,
        )
    except CaseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CASE_NOT_FOUND",
                "message": f"Case was not found: {case_id}",
            },
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "COMPARE_CANDIDATES_UNAVAILABLE",
                "message": "Compare candidate DB is unavailable.",
            },
        ) from exc
