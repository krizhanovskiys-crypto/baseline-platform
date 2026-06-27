"""Async database session management.

Usage inside FastAPI:
    Depends(get_db_session)

Usage inside bot handlers — pass through service layer only.
"""
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import get_settings
from backend.app.database.base import Base  # noqa: F401 — ensures models load

logger = logging.getLogger(__name__)

_settings = get_settings()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_connect_args: dict = {}
if _settings.is_sqlite:
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.debug,
    connect_args=_connect_args,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context-manager that yields an AsyncSession and handles commit/rollback."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an AsyncSession per request."""
    async with get_session() as session:
        yield session


async def create_all_tables() -> None:
    """Create all tables.  Called on application startup in development."""
    # Import all models so SQLAlchemy knows about them
    import backend.app.database.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified.")
