import pytest

from app.etl.extract import EXPECTED_FILES, extract_all


def test_extract_all_reads_every_expected_file(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    assert set(datasets.keys()) == set(EXPECTED_FILES)


def test_extract_all_preserves_row_counts(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    assert len(datasets["saleshourly.csv"].frame) == 4
    assert len(datasets["salesdaily.csv"].frame) == 2
    assert len(datasets["salesweekly.csv"].frame) == 1
    assert len(datasets["salesmonthly.csv"].frame) == 1


def test_extract_all_raises_loudly_when_files_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="Missing expected raw source file"):
        extract_all(tmp_path)
