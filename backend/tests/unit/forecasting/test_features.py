import pandas as pd

from app.forecasting.features import (
    MIN_WARMUP_DAYS,
    add_calendar_features,
    add_lag_features,
    add_rolling_features,
    build_feature_frame,
    make_training_table,
)


def _series_frame(n_days: int, start: str = "2020-01-01"):
    dates = pd.date_range(start, periods=n_days, freq="D")
    values = list(range(1, n_days + 1))  # 1, 2, 3, ... — easy to hand-verify
    return pd.DataFrame({"observation_date": dates, "units_sold": values})


def test_lag_features_correct_values():
    df = add_lag_features(_series_frame(10))
    # lag_1 on day i (1-indexed values) should equal the previous day's value
    assert df["lag_1"].iloc[5] == df["units_sold"].iloc[4]
    assert df["lag_7"].iloc[9] == df["units_sold"].iloc[2]
    assert df["lag_1"].iloc[0] != df["lag_1"].iloc[0]  # NaN for the very first row (no prior day)


def test_rolling_mean_is_shifted_and_excludes_current_day():
    df = _series_frame(10)  # values 1..10
    out = add_rolling_features(df, windows=(3,))
    # rolling_mean_3 at row index 5 (value=6) should average values at
    # indices 2,3,4 (values 3,4,5) = 4.0 -- NEVER including index 5 itself.
    assert out["rolling_mean_3"].iloc[5] == 4.0


def test_rolling_feature_unaffected_by_changing_the_current_or_future_row():
    """THE explicit leakage test (M4 Sec. 18): if a future observation
    were to leak into a lag/rolling feature computed for an earlier date,
    changing that future value would change the earlier feature. It must
    not."""
    df = _series_frame(20)
    baseline = add_rolling_features(df.copy(), windows=(7,))
    baseline_value_at_10 = baseline["rolling_mean_7"].iloc[10]

    mutated = df.copy()
    mutated.loc[mutated.index[10:], "units_sold"] = 99999.0  # mutate day 10 onward
    mutated_features = add_rolling_features(mutated, windows=(7,))

    # Every row STRICTLY BEFORE index 10 must be byte-for-byte identical --
    # they cannot have seen the mutation at all.
    pd.testing.assert_series_equal(
        baseline["rolling_mean_7"].iloc[:10], mutated_features["rolling_mean_7"].iloc[:10]
    )
    # And the feature AT index 10 itself must also be unaffected, since it
    # only ever sees days [3..9], never day 10's own (mutated) value.
    assert mutated_features["rolling_mean_7"].iloc[10] == baseline_value_at_10


def test_lag_feature_unaffected_by_changing_a_later_row():
    df = _series_frame(20)
    baseline = add_lag_features(df.copy(), lags=(1,))
    mutated = df.copy()
    mutated.loc[mutated.index[15:], "units_sold"] = -1.0
    mutated_features = add_lag_features(mutated, lags=(1,))
    pd.testing.assert_series_equal(baseline["lag_1"].iloc[:15], mutated_features["lag_1"].iloc[:15])


def test_calendar_features_are_date_derived_not_leakage():
    df = _series_frame(8, start="2020-01-06")  # a Monday
    out = add_calendar_features(df)
    assert out["day_of_week"].iloc[0] == 0  # Monday
    assert out["is_weekend"].iloc[5] == 1  # Saturday (index 5 = 2020-01-11)
    assert out["month"].iloc[0] == 1


def test_make_training_table_drops_warmup_rows_with_nan_features():
    df = _series_frame(MIN_WARMUP_DAYS + 10)
    featured = build_feature_frame(df)
    X, y, feature_cols = make_training_table(featured)
    # every row before the longest window/lag is satisfied must be dropped
    assert len(X) == 10
    assert not X.isna().any().any()
    assert len(y) == len(X)
    assert set(feature_cols) <= set(featured.columns)


def test_make_training_table_empty_when_insufficient_history():
    df = _series_frame(5)  # far short of MIN_WARMUP_DAYS
    featured = build_feature_frame(df)
    X, y, _ = make_training_table(featured)
    assert len(X) == 0
    assert len(y) == 0
