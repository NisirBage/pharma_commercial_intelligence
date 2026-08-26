from app.etl.extract import extract_all
from app.etl.transform import (
    transform_canonical_fact,
    transform_daily_staging,
    transform_hourly_staging,
    transform_monthly_staging,
    transform_weekly_staging,
)


def test_transform_hourly_staging_renames_and_types(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    df = transform_hourly_staging(datasets["saleshourly.csv"])
    assert list(df.columns) == [
        "datum_raw", "observation_ts", "m01ab", "m01ae", "n02ba", "n02be",
        "n05b", "n05c", "r03", "r06", "year", "month", "hour_of_day", "weekday_name",
    ]
    assert len(df) == 4
    assert df["observation_ts"].dtype.kind == "M"  # datetime64


def test_transform_daily_staging_renames_hour_to_artifact(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    df = transform_daily_staging(datasets["salesdaily.csv"])
    assert "hour_sum_artifact" in df.columns
    assert "Hour" not in df.columns
    assert df["hour_sum_artifact"].tolist() == [17, 17]


def test_transform_weekly_staging_shape(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    df = transform_weekly_staging(datasets["salesweekly.csv"])
    assert list(df.columns) == ["datum_raw", "week_ending_date", "m01ab", "m01ae", "n02ba", "n02be", "n05b", "n05c", "r03", "r06"]
    assert len(df) == 1


def test_transform_monthly_staging_is_reconciled_always_false(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    df = transform_monthly_staging(datasets["salesmonthly.csv"])
    assert (df["is_reconciled"] == False).all()  # noqa: E712


def test_transform_canonical_fact_melts_wide_to_long_without_loss(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    hourly_staging = transform_hourly_staging(datasets["saleshourly.csv"])
    long_df = transform_canonical_fact(hourly_staging)

    # 4 source rows * 8 ATC classes = 32 long rows, no rows dropped
    assert len(long_df) == 4 * 8
    assert set(long_df["atc_code"].unique()) == {
        "M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"
    }

    # total units summed back up must equal the sum of every wide product cell
    wide_total = hourly_staging[["m01ab", "m01ae", "n02ba", "n02be", "n05b", "n05c", "r03", "r06"]].to_numpy().sum()
    assert long_df["units_sold"].sum() == wide_total
