"""Aggregates every route module under its correct prefix. `/health` is
unversioned (standard convention for a liveness probe); everything else
lives under `/api/v1` (M6 Sec. 4 — "version the API")."""

from fastapi import APIRouter

from app.api.routes import (
    analytics,
    anomalies,
    data_quality,
    forecasts,
    health,
    kpis,
    optimization,
    recommendations,
    sales,
)

api_router = APIRouter()
api_router.include_router(health.router)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(kpis.router)
v1_router.include_router(sales.router)
v1_router.include_router(analytics.router)
v1_router.include_router(anomalies.router)
v1_router.include_router(forecasts.router)
v1_router.include_router(optimization.router)
v1_router.include_router(recommendations.router)
v1_router.include_router(data_quality.router)

api_router.include_router(v1_router)
