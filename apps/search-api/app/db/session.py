from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from app.core.config import settings


def _sqlalchemy_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(
    _sqlalchemy_database_url(settings.database_url),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    connect_args={"connect_timeout": 10},
)


def get_connection() -> Iterator[Connection]:
    with engine.connect() as connection:
        yield connection
