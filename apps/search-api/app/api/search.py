from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_connection
from app.repositories.statute_search import PostgresStatuteSearchRepository
from app.schemas.search import (
    ErrorResponse,
    NaturalSearchRequest,
    NaturalSearchResponse,
    StatuteSearchRequest,
    StatuteSearchResponse,
)
from app.services.article_normalizer import ArticleParseError
from app.services.statute_search import ArticleNotFoundError, StatuteSearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


def get_statute_search_service(
    connection: Connection = Depends(get_connection),
) -> Iterator[StatuteSearchService]:
    yield StatuteSearchService(PostgresStatuteSearchRepository(connection))


@router.post(
    "/statute",
    response_model=StatuteSearchResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def search_statute(
    request: StatuteSearchRequest,
    service: StatuteSearchService = Depends(get_statute_search_service),
) -> StatuteSearchResponse:
    try:
        return service.search(
            query=request.query,
            page=request.page,
            size=request.size,
            sort=request.sort,
        )
    except ArticleParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PARSE_FAILED", "message": str(exc)},
        ) from exc
    except ArticleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ARTICLE_NOT_FOUND",
                "message": f"Article was not found in the internal DB: {exc}",
            },
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SEARCH_UNAVAILABLE",
                "message": "Search DB is unavailable.",
            },
        ) from exc


@router.post(
    "/natural",
    response_model=NaturalSearchResponse,
    responses={
        503: {"model": ErrorResponse},
    },
)
def search_natural(
    request: NaturalSearchRequest,
    service: StatuteSearchService = Depends(get_statute_search_service),
) -> NaturalSearchResponse:
    try:
        return service.search_natural(
            query=request.query,
            page=request.page,
            size=request.size,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "SEARCH_UNAVAILABLE",
                "message": "Search DB is unavailable.",
            },
        ) from exc
