import json

from app.etl.extract import extract_all
from app.etl.quality_report import build_report, summarize_dataset, write_report
from app.etl.validate import validate_all


def test_summarize_dataset_all_rows_valid_on_clean_fixture(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    summary = summarize_dataset(datasets["salesdaily.csv"])
    assert summary["total_records"] == 2
    assert summary["valid_records"] == 2
    assert summary["rejected_records"] == 0


def test_build_report_overall_status_is_warn_when_only_warn_present(raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    results = validate_all(datasets)
    report = build_report(datasets, results, "milanzdravkovic/pharma-sales-data")
    # fixture's monthly file deliberately mismatches -> warn; nothing should fail
    assert report["overall_status"] == "warn"
    assert len(report["file_summaries"]) == 4
    assert len(report["checks"]) == len(results)


def test_write_report_produces_valid_json_file(tmp_path, raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    results = validate_all(datasets)
    report = build_report(datasets, results, "milanzdravkovic/pharma-sales-data")
    path = write_report(report, tmp_path, run_id=42)
    assert path.exists()
    assert "_run42" in path.name
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["overall_status"] == "warn"
