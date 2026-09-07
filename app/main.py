"""FastAPI application entry point for TOKI Backend.

Implements the modular monolith application assembly, lifespan events,
profile validation at startup, and health routing.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.api.health import router as health_router
from app.api.progress import router as progress_router
from app.api.sessions import router as sessions_router
from app.config.settings import ConfigurationError, Profile, get_settings

logger = logging.getLogger("toki")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: validate settings at startup, cleanup at shutdown."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger.info(
        "Starting TOKI Backend v%s [profile=%s, env=%s]",
        __version__,
        settings.profile.value,
        settings.env.value,
    )

    # Validate settings invariants at startup
    try:
        settings.check_startup_invariants()
    except ConfigurationError as exc:
        logger.error("Configuration validation failed at boot: %s", exc)
        raise SystemExit(f"Configuration validation failed: {exc}") from exc

    yield

    logger.info("Shutting down TOKI Backend gracefully")


def create_app() -> FastAPI:
    """Application factory for TOKI Backend."""
    settings = get_settings()

    # Docs are enabled in non-production environments
    enable_docs = settings.profile in (Profile.LOCAL, Profile.TEST, Profile.DEMO_OFFLINE)

    app = FastAPI(
        title="TOKI — Backend & Conversational AI",
        description="Educational companion API for Indonesian child speech stimulation (LIDM 2026)",
        version=__version__,
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        lifespan=lifespan,
    )

    # Exception handler for configuration errors
    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(
        request: Request, exc: ConfigurationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "ConfigurationError", "message": str(exc)},
        )

    # Register API routers
    app.include_router(health_router)
    app.include_router(progress_router)
    app.include_router(sessions_router)

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        return {
            "name": "TOKI Backend",
            "version": __version__,
            "status": "OPERATIONAL",
            "profile": settings.profile.value,
        }

    return app


app = create_app()
