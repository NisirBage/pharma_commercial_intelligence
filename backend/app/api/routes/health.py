from fastapi import APIRouter

from app.api.deps import check_database_connection
from app.core.config import settings
from app.schemas.common import SuccessResponse
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=SuccessResponse[HealthResponse], summary="Application health check")
def health_check() -> SuccessResponse[HealthResponse]:
    """Lightweight liveness check — at most one trivial `SELECT 1` against
    the database (M6 Sec. 6), never analytics/forecasting/optimization
    work. Reports `database: "unreachable"` rather than failing the whole
    request when no Postgres is configured: this project's primary data
    path is the CSV-derived canonical frame (app.analytics.data_access),
    so a missing database does not by itself make the API unhealthy."""
    db_status = check_database_connection()
    return SuccessResponse(
        data=HealthResponse(status="ok", version=settings.api_version, environment=settings.environment, database=db_status)
    )
