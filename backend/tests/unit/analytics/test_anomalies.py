import pandas as pd

from app.analytics import anomalies
from tests.unit.analytics.helpers import daily_series_frame, make_frame


def _baseline(n_days: int) -> list[float]:
    """Deterministic mild oscillation (mean ~100, std ~4) — enough natural
    variation to exercise the rolling-std machinery without ever crossing
    the z=2 anomaly threshold on its own."""
    pattern = [95, 100, 105, 100]
    return [pattern[i % 4] for i in range(n_days)]


def test_detect_rolling_zscore_no_anomalies_in_stable_data():
    frame = daily_series_frame("M01AB", "2020-01-01", _baseline(45))
    assert anomalies.detect_rolling_zscore(frame, "M01AB") == []


def test_detect_rolling_zscore_flags_positive_spike():
    values = _baseline(40) + [500.0]
    frame = daily_series_frame("M01AB", "2020-01-01", values)
    result = anomalies.detect_rolling_zscore(frame, "M01AB")
    assert len(result) == 1
    assert result[0].direction == "above"
    assert result[0].severity == "high"
    assert result[0].observed == 500.0
    assert result[0].method == "rolling_zscore"


def test_detect_rolling_zscore_flags_negative_drop():
    values = _baseline(40) + [1.0]
    frame = daily_series_frame("M01AB", "2020-01-01", values)
    result = anomalies.detect_rolling_zscore(frame, "M01AB")
    assert len(result) == 1
    assert result[0].direction == "below"


def test_detect_rolling_zscore_constant_series_yields_no_anomalies():
    """Zero-variance baseline (a perfectly flat run) can't produce a
    z-score at all — documented limitation, not a false positive."""
    frame = daily_series_frame("M01AB", "2020-01-01", [50.0] * 45)
    assert anomalies.detect_rolling_zscore(frame, "M01AB") == []


def test_detect_rolling_zscore_insufficient_history():
    frame = daily_series_frame("M01AB", "2020-01-01", [10.0] * 10)  # < MIN_HISTORY_DAYS
    assert anomalies.detect_rolling_zscore(frame, "M01AB") == []


def test_detect_iqr_flags_spike():
    values = _baseline(40) + [500.0]
    frame = daily_series_frame("M01AB", "2020-01-01", values)
    result = anomalies.detect_iqr(frame, "M01AB")
    assert len(result) == 1
    assert result[0].direction == "above"
    assert result[0].method == "iqr"


def test_detect_iqr_constant_series_yields_no_anomalies():
    frame = daily_series_frame("M01AB", "2020-01-01", [50.0] * 45)
    assert anomalies.detect_iqr(frame, "M01AB") == []


def test_detect_anomalies_runs_across_all_atc_classes_independently():
    frame = pd.concat(
        [
            daily_series_frame("M01AB", "2020-01-01", _baseline(40) + [500.0]),
            daily_series_frame("N05B", "2020-01-01", _baseline(45)),  # stable, no anomaly expected
        ]
    )
    result = anomalies.detect_anomalies(frame, methods=("rolling_zscore",))
    assert {a.atc_class for a in result} == {"M01AB"}


def test_detect_anomalies_empty_dataset():
    assert anomalies.detect_anomalies(make_frame([])) == []


def test_detect_mean_shift_finds_level_change():
    values = [9.0, 11.0] * 20 + [49.0, 51.0] * 20  # clear level shift halfway through, mild internal variance
    frame = daily_series_frame("M01AB", "2020-01-01", values)
    result = anomalies.detect_mean_shift(frame, grain="daily")
    assert result.value is not None
    assert result.metadata["mean_after"] > result.metadata["mean_before"]
    assert result.metadata["p_value_uncorrected"] < 0.05


def test_detect_mean_shift_insufficient_periods():
    frame = daily_series_frame("M01AB", "2020-01-01", [10.0] * 4)  # < MIN_CHANGE_POINT_SEGMENT * 2
    result = anomalies.detect_mean_shift(frame, grain="daily")
    assert result.value is None
    assert result.metadata["reason"] == "insufficient_periods"


def test_detect_mean_shift_empty_dataset():
    result = anomalies.detect_mean_shift(make_frame([]))
    assert result.metadata["reason"] == "no_data"
