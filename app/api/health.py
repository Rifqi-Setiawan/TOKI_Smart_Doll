"""Health check endpoints with distinct liveness, readiness, and demo semantics (API-007)."""

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app import __version__
from app.config.settings import Profile, Settings, get_settings

router = APIRouter(prefix="/health", tags=["Health"])


class LiveStatus(BaseModel):
    status: str = Field(default="LIVE", description="Process liveness indicator")
    profile: str = Field(description="Active runtime profile")
    version: str = Field(default=__version__, description="Application version")


class ReadyStatus(BaseModel):
    status: str = Field(description="'READY' or 'NOT_READY'")
    profile: str = Field(description="Active runtime profile")
    database: str = Field(description="Core persistence status")
    reason: str | None = Field(default=None, description="Failure reason if not ready")


class ProviderStatus(BaseModel):
    asr: str
    tts: str
    semantic: str
    vision: str


class DemoStatus(BaseModel):
    status: str = Field(description="'HEALTHY' or 'DEGRADED'")
    profile: str = Field(description="Active runtime profile")
    core_ready: bool = Field(description="Whether core activity engine is operational")
    providers: ProviderStatus
    degraded_reasons: list[str] = Field(default_factory=list)


async def check_database_readiness(settings: Settings) -> tuple[bool, str]:
    """Check database connectivity.

    In test profile or when database is reachable, returns (True, 'READY').
    Can be replaced or extended with an actual DB ping in TASK-004.
    """
    if settings.profile == Profile.TEST:
        return True, "READY"

    # Minimal connectivity check hook
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(
            settings.database_url,
            connect_args={"timeout": 2},
            pool_pre_ping=True,
        )
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True, "READY"
    except Exception as exc:
        return False, f"Database connection unavailable: {exc.__class__.__name__}"


@router.get(
    "/live",
    response_model=LiveStatus,
    summary="Process liveness probe",
    description="Returns 200 OK as long as the process is alive and HTTP event loop is responsive.",
)
async def get_live(settings: Settings = Depends(get_settings)) -> LiveStatus:
    return LiveStatus(status="LIVE", profile=settings.profile.value, version=__version__)


@router.get(
    "/ready",
    response_model=ReadyStatus,
    summary="Core service readiness probe",
    description=(
        "Returns 200 OK when core dependencies (config, DB) are ready. "
        "Returns 503 if core is not ready."
    ),
)
async def get_ready(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> ReadyStatus:
    db_ok, db_msg = await check_database_readiness(settings)

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyStatus(
            status="NOT_READY",
            profile=settings.profile.value,
            database="NOT_READY",
            reason=db_msg,
        )

    return ReadyStatus(
        status="READY",
        profile=settings.profile.value,
        database="READY",
        reason=None,
    )


@router.get(
    "/demo",
    response_model=DemoStatus,
    summary="Demo degradation health probe",
    description=(
        "Reports status of optional providers and demo adapters. "
        "Optional provider degradation does NOT fail process liveness or core readiness."
    ),
)
async def get_demo(settings: Settings = Depends(get_settings)) -> DemoStatus:
    degraded_reasons: list[str] = []

    # Assess speech adapters
    asr_status = settings.asr_provider
    if settings.asr_provider == "managed" and not settings.cloud_asr_api_key:
        degraded_reasons.append("Managed ASR missing cloud key; falling back to fake/cached")
        asr_status = "degraded"

    tts_status = settings.tts_provider
    if settings.tts_provider == "managed" and not settings.cloud_tts_api_key:
        degraded_reasons.append("Managed TTS missing cloud key; falling back to cached")
        tts_status = "degraded"

    # Assess optional AI components
    semantic_status = "enabled" if settings.semantic_enabled else "disabled"
    is_cloud = settings.profile == Profile.CLOUD
    if settings.semantic_enabled and not settings.cloud_llm_api_key and is_cloud:
        degraded_reasons.append("Semantic resolver enabled without cloud credentials")
        semantic_status = "degraded"

    vision_status = "enabled" if settings.vision_enabled else "disabled"

    overall_status = "DEGRADED" if degraded_reasons else "HEALTHY"

    return DemoStatus(
        status=overall_status,
        profile=settings.profile.value,
        core_ready=True,
        providers=ProviderStatus(
            asr=asr_status,
            tts=tts_status,
            semantic=semantic_status,
            vision=vision_status,
        ),
        degraded_reasons=degraded_reasons,
    )
