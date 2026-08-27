"""In-process caches for the expensive, deterministic-until-the-data-
changes computations the API sits on top of: the canonical demand frame
(M2/M3 — roughly 1-2s to rebuild from the raw CSVs) and per-ATC-class
demand inputs (M5 — which re-runs an M4 backtest per class to recover
residuals, roughly 7-14s total across 8 classes). Both are wrapped in
`functools.lru_cache` so the FIRST request pays the cost and every
subsequent request in this process's lifetime is instant — this is what
M6 Sec. 26 ("never trigger the complete M4 backtest suite for every HTTP
request") means in code.

**This is an in-process, process-LIFETIME cache — a documented
simplification** (see docs/api-design.md, "Caching strategy"). A
production deployment would instead persist these to a proper cache
(Redis, or a materialized table) with explicit invalidation tied to when
the M4/M5 pipelines actually rerun — not "however long this process
happens to stay up." `clear_all_caches()` is the seam a future
invalidation trigger (or admin endpoint) would call.
"""

from functools import lru_cache

import pandas as pd

from app.analytics import kpis
from app.analytics.data_access import load_from_raw_csv
from app.analytics.reconciliation import build_reconciliation_report
from app.core.config import settings
from app.etl.extract import extract_all
from app.etl.quality_report import build_report
from app.etl.validate import validate_all
from app.optimization.demand_input import DemandInput, build_all_demand_inputs


@lru_cache(maxsize=1)
def get_canonical_frame() -> pd.DataFrame:
    return load_from_raw_csv()


@lru_cache(maxsize=1)
def get_demand_inputs() -> dict[str, DemandInput]:
    """Raises ValueError (translated to a 503 by the forecast/optimization
    services — app.api.errors.ServiceUnavailableError) if the M4 model
    registry hasn't been populated yet (run backend/scripts/run_m4_backtest.py)."""
    return build_all_demand_inputs()


@lru_cache(maxsize=1)
def get_contributions() -> dict[str, float]:
    df = get_canonical_frame()
    return {m.entity: m.value for m in kpis.contribution_by_atc(df)}


@lru_cache(maxsize=1)
def get_quality_report() -> dict:
    datasets = extract_all(settings.raw_data_dir)
    check_results = validate_all(datasets)
    return build_report(datasets, check_results, settings.kaggle_dataset_id)


@lru_cache(maxsize=1)
def get_reconciliation_report() -> dict:
    return build_reconciliation_report(settings.raw_data_dir)


def clear_all_caches() -> None:
    """Forces every cache to recompute on next access. Used by tests, and
    the seam a future cache-invalidation trigger would call."""
    get_canonical_frame.cache_clear()
    get_demand_inputs.cache_clear()
    get_contributions.cache_clear()
    get_quality_report.cache_clear()
    get_reconciliation_report.cache_clear()
