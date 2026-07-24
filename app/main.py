"""
FastAPI application factory and lifespan management.

Design Decision:
    We use a factory pattern (create_app function) instead of a module-level
    FastAPI instance. This provides:
    1. Testability — tests can create fresh app instances.
    2. Configuration injection — different settings for test vs production.
    3. Clean startup/shutdown — lifespan context manager handles resource lifecycle.

    The lifespan context manager (PEP 3143 pattern) replaces the deprecated
    @app.on_event("startup") / @app.on_event("shutdown") hooks.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.routes import router as api_router
from app.config.settings import settings
from app.utils.logger import get_logger, setup_root_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application startup and shutdown lifecycle.

    Startup:
        - Configure the root logger.
        - Create required directories (uploads, logs).
        - Log startup confirmation.

    Shutdown:
        - Log shutdown confirmation.
        - Future: close database connections, flush caches.

    Args:
        app: The FastAPI application instance.

    Yields:
        None — control passes to the application during its lifetime.
    """
    # --- Startup ---
    setup_root_logger(log_level=settings.log_level, log_dir=settings.log_dir)
    settings.ensure_directories()
    logger.info(
        "Application starting — API at %s:%d",
        settings.api_host,
        settings.api_port,
    )

    yield  # Application runs here

    # --- Shutdown ---
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This factory function:
    1. Creates the FastAPI instance with metadata for OpenAPI docs.
    2. Attaches the lifespan context manager for startup/shutdown.
    3. Mounts all API routers.

    Returns:
        A fully configured FastAPI application instance.
    """
    app = FastAPI(
        title="AI Resume Screening Bot",
        description=(
            "AI-powered resume screening and candidate ranking service. "
            "Performs intelligent resume analysis, skill matching, and "
            "provides explainable scoring with learning recommendations."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # Mount API routes
    app.include_router(api_router)

    logger.info("FastAPI application created with routes mounted")
    return app
