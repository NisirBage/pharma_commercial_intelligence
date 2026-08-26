from app.analytics.reconciliation import build_reconciliation_report


def test_reconciliation_report_daily_and_weekly_pass_monthly_warns(raw_fixture_dir):
    """Reuses the M2 fixture (tests/fixtures/pharma_mini) whose
    salesmonthly.csv has a deliberate mismatch — same property the real
    dataset exhibits (docs/data-quality-decisions.md Decision 2)."""
    report = build_reconciliation_report(raw_fixture_dir)

    assert report["summary"]["Daily"]["reconciled"] is True
    assert report["summary"]["Weekly"]["reconciled"] is True
    assert report["summary"]["Monthly"]["reconciled"] is False
    assert report["summary"]["Monthly"]["status"] == "warn"

    assert "Daily:\nReconciled" in report["human_readable"]
    assert "Weekly:\nReconciled" in report["human_readable"]
    assert "Monthly:\nSource inconsistency detected" in report["human_readable"]

    assert report["all_reconciled_except_known_monthly_issue"] is True
