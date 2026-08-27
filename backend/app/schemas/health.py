from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    version: str
    environment: str
    database: str  # "connected" | "unreachable" | "not_configured"
