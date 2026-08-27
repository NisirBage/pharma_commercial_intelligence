"""The 8 observed ATC classes (M1/M2) — the single place every service
that needs to validate an ATC-class path/query parameter imports this
from, so "unknown ATC class" is defined once, not per endpoint."""

KNOWN_ATC_CLASSES: frozenset[str] = frozenset({"M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"})

# Forecast/optimization entities additionally include "ALL" (the
# aggregate series, M4) — kept separate since not every endpoint accepts it
# (e.g. /analytics/atc and /optimization/run are always per-class-only).
KNOWN_FORECAST_ENTITIES: frozenset[str] = KNOWN_ATC_CLASSES | {"ALL"}
