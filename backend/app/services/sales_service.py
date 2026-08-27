"""Wraps app.analytics.aggregate (M3's single rollup path) for
GET /api/v1/sales/trends — input validation lives here, not in the route
or scattered across query-parameter defaults."""

from app.analytics.aggregate import GRAIN_FUNCS
from app.api.errors import NotFoundError
from app.schemas.sales import Grain, SalesTrendsResponse, TrendPoint
from app.services import cache
from app.services.atc_registry import KNOWN_ATC_CLASSES
from app.services.validation import validate_date_range

_GRAIN_PERIOD_COL = {"daily": "observation_date", "weekly": "week_ending_date", "monthly": "month_start_date"}


def get_sales_trends(
    atc_class: str | None, start_date: str | None, end_date: str | None, grain: Grain
) -> SalesTrendsResponse:
    if atc_class is not None and atc_class not in KNOWN_ATC_CLASSES:
        raise NotFoundError(f"Unknown ATC class {atc_class!r}. Known classes: {sorted(KNOWN_ATC_CLASSES)}.")

    parsed_start, parsed_end = validate_date_range(start_date, end_date)

    df = cache.get_canonical_frame()
    frame = df if atc_class is None else df[df["atc_code"] == atc_class]
    if parsed_start:
        frame = frame[frame["observation_ts"].dt.date >= parsed_start]
    if parsed_end:
        frame = frame[frame["observation_ts"].dt.date <= parsed_end]

    if frame.empty:
        return SalesTrendsResponse(
            atc_class=atc_class, grain=grain, start_date=start_date or "", end_date=end_date or "", points=[]
        )

    rolled = GRAIN_FUNCS[grain.value](frame, by_atc=False)
    period_col = _GRAIN_PERIOD_COL[grain.value]
    rolled = rolled.sort_values(period_col)

    points = [
        TrendPoint(period=str(row[period_col].date()), units_sold=float(row["units_sold"]))
        for _, row in rolled.iterrows()
    ]

    return SalesTrendsResponse(
        atc_class=atc_class,
        grain=grain,
        start_date=str(frame["observation_ts"].min().date()),
        end_date=str(frame["observation_ts"].max().date()),
        points=points,
    )
