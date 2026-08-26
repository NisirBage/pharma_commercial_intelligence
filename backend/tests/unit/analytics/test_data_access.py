from app.analytics.data_access import CANONICAL_COLUMNS, load_canonical_frame, load_from_raw_csv


def test_load_from_raw_csv_matches_canonical_shape(raw_fixture_dir):
    df = load_from_raw_csv(raw_fixture_dir)
    assert list(df.columns) == CANONICAL_COLUMNS
    # fixture has 4 hourly rows * 8 ATC classes = 32 canonical rows (see M2 fixture)
    assert len(df) == 32
    assert set(df["atc_code"].unique()) == {"M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"}
    assert df["observation_ts"].is_monotonic_increasing


def test_load_canonical_frame_defaults_to_csv_when_no_session(raw_fixture_dir):
    df = load_canonical_frame(session=None, raw_data_dir=raw_fixture_dir)
    assert len(df) == 32
