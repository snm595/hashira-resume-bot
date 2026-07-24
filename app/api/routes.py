"""
FastAPI route definitions.

Design Decision:
    Routes are defined on an APIRouter, not directly on the FastAPI app.
    This allows:
    1. Modular composition — multiple routers can be mounted with prefixes.
    2. Testability — routers can be tested in isolation.
    3. Organization — routes are grouped by domain (health, upload, process).

    Phase 1 only includes the health check endpoint. Future phases will
    add /upload/jd, /upload/resume, /process, and /candidate/{id}
    as specified in PRD §11.
"""

from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Router instance with a descriptive prefix and tag for OpenAPI docs.
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api", tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the current health status of the application. "
    "Used by monitoring tools and load balancers.",
)
async def health_check() -> HealthResponse:
    """
    Return the current health status of the application.

    This endpoint is intentionally lightweight — no database queries,
    no external API calls. It simply confirms the service is running
    and responding to requests.

    Returns:
        HealthResponse with status, version, and current timestamp.
    """
    logger.debug("Health check requested")
    return HealthResponse()
