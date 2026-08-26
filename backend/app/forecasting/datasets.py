"""Chronological dataset preparation for forecasting.

Builds one clean, gap-free, strictly-ordered daily series per ATC class
(plus one aggregate "ALL" series) from the canonical hourly frame — never
from `salesmonthly.csv` (M2 Decision 2). Every date in the observed range
gets a row, including days with zero recorded sales (a genuine
observation per M1/M2, not a gap — see docs/01-data-dictionary.md).
Missing calendar dates (if any) are surfaced explicitly rather than
silently dropped or interpolated, since interpolating a value the source
never reported would itself be a form of fabrication.
"""

from dataclasses import dataclass

import pandas as pd

from app.analytics.aggregate import to_daily

DATE_COL = "observation_date"
TARGET_COL = "units_sold"
AGGREGATE_ENTITY = "ALL"


@dataclass
class SeriesPrepResult:
    entity: str
    frame: pd.DataFrame  # columns: [observation_date, units_sold], one row per calendar day, no gaps
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    n_days: int
    missing_dates_filled: list[str]  # dates that were absent from the source and filled with 0.0
    duplicate_dates_found: int


def _prepare_single_series(daily: pd.DataFrame, entity: str) -> SeriesPrepResult:
    daily = daily.sort_values(DATE_COL).reset_index(drop=True)

    duplicate_dates_found = int(daily[DATE_COL].duplicated().sum())
    if duplicate_dates_found:
        # Collapse duplicates by summing — should never happen given M2's
        # UNIQUE(observation_ts) constraint upstream, but a forecasting
        # module must not silently assume its input is clean.
        daily = daily.groupby(DATE_COL, as_index=False)[TARGET_COL].sum()

    full_index = pd.date_range(daily[DATE_COL].min(), daily[DATE_COL].max(), freq="D")
    reindexed = daily.set_index(DATE_COL).reindex(full_index)
    missing_dates_filled = [str(d.date()) for d in reindexed.index[reindexed[TARGET_COL].isna()]]
    reindexed[TARGET_COL] = reindexed[TARGET_COL].fillna(0.0)
    reindexed = reindexed.rename_axis(DATE_COL).reset_index()

    return SeriesPrepResult(
        entity=entity,
        frame=reindexed[[DATE_COL, TARGET_COL]],
        start_date=reindexed[DATE_COL].min(),
        end_date=reindexed[DATE_COL].max(),
        n_days=len(reindexed),
        missing_dates_filled=missing_dates_filled,
        duplicate_dates_found=duplicate_dates_found,
    )


def build_daily_series(canonical_df: pd.DataFrame, entity: str | None = None) -> SeriesPrepResult:
    """`entity=None` or `entity="ALL"` builds the aggregate (summed across
    every ATC class) series; otherwise builds the single-class series."""
    if entity is None or entity == AGGREGATE_ENTITY:
        daily = to_daily(canonical_df, by_atc=False)
        return _prepare_single_series(daily, AGGREGATE_ENTITY)

    frame = canonical_df[canonical_df["atc_code"] == entity]
    daily = to_daily(frame, by_atc=False)
    return _prepare_single_series(daily, entity)


def build_all_series(canonical_df: pd.DataFrame) -> dict[str, SeriesPrepResult]:
    """One entry per observed ATC class, plus one `"ALL"` aggregate entry."""
    results = {AGGREGATE_ENTITY: build_daily_series(canonical_df, AGGREGATE_ENTITY)}
    for atc in sorted(canonical_df["atc_code"].unique()):
        results[atc] = build_daily_series(canonical_df, atc)
    return results
