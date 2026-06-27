"""FastAPI application factory.

Run with:
    uvicorn backend.app.api.app:app --reload
"""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1 import router as api_v1_router
from backend.app.core.config import get_settings
from backend.app.core.logging import setup_logging
from backend.app.database.session import create_all_tables

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup → yield → shutdown."""
    setup_logging()
    await create_all_tables()
    logger.info("Baseline API started.")
    yield
    logger.info("Baseline API shutting down.")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Baseline API",
        description="Tennis matchmaking platform REST API",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "service": "baseline-api"}

    return app


app = create_app()
