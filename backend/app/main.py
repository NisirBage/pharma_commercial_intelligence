"""FastAPI application entrypoint.

    Frontend
       |
    FastAPI (this app)                     <- app/api/routes/*.py (thin handlers)
       |
    Service layer                          <- app/services/*.py (request/response translation, validation, caching)
       |
    Analytics / Forecasting / Optimization  <- app/analytics, app/forecasting, app/optimization (M3/M4/M5 — unmodified)
       |
    Data access                            <- app/analytics/data_access.py, app/optimization/demand_input.py
       |
    Database / canonical CSV-derived data  <- M2

Run locally (from backend/):
    uvicorn app.main:app --reload

Interactive docs once running: http://localhost:8000/docs (Swagger) and
http://localhost:8000/redoc. See docs/api-design.md for the full
architecture write-up, caching strategy, and security review.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware import RequestLoggingMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description=(
        "Business-facing API over the Pharma Commercial Intelligence & Supply Planning Platform's existing "
        "M2 (canonical data), M3 (analytics), M4 (forecasting), and M5 (optimization) capabilities. "
        "Every response distinguishes data observed in the source dataset from scenario planning "
        "assumptions — see the `assumptions` field on optimization responses, and "
        "docs/planning-assumptions.md in the repository."
    ),
)

# CORS: never allow_origins=["*"] — origins are explicit and configurable
# via CORS_ALLOWED_ORIGINS (defaults to the Vite dev server only). See
# docs/api-design.md, "CORS", for the reasoning.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)
app.include_router(api_router)
