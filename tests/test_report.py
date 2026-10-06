from datetime import datetime

from backend.simulation.report import format_report, run_baseline


def test_three_day_baseline_is_repeatable_and_reviewable():
    summary = run_baseline(3, datetime(2026, 1, 1, 9))
    assert len(summary["events"]) == 72
    assert summary["counts"]["ACT"] > 0
    assert summary["counts"]["WAIT"] > summary["counts"]["ACT"]
    assert summary["events"][0]["decision"] == "WAIT"


def test_report_contains_decisions_and_intents():
    report = format_report(run_baseline(1, datetime(2026, 1, 1, 9)))
    assert "Milestone 1 Baseline Simulation" in report
    assert "ACT" in report
    assert "WAIT" in report
    assert "reach out to the player" in report
