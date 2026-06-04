from __future__ import annotations

from fastapi import FastAPI

from app.api.cases import router as cases_router
from app.api.compare import router as compare_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="CaseLens Search API",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(cases_router)
    app.include_router(compare_router)
    app.include_router(feedback_router)
    return app


app = create_app()
