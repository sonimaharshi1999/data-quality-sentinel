# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Tests for the trend tracking SQLite store.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from sentinel.models import CheckResult, CheckType, Severity, ValidationReport
from sentinel.trend import TrendStore


def _make_report(suite_name: str = "test_suite", score: float = 85.0) -> ValidationReport:
    """Helper to create a minimal ValidationReport for testing."""
    return ValidationReport(
        suite_name=suite_name,
        data_source="test_source",
        run_id="abc12345",
        total_checks=10,
        passed_checks=8,
        failed_checks=2,
        warning_checks=1,
        critical_failures=1,
        check_results=[
            CheckResult(
                check_name="test_check",
                check_type=CheckType.NOT_NULL,
                column="col1",
                passed=True,
                severity=Severity.CRITICAL,
                message="All good",
                rows_checked=100,
                rows_failed=0,
            ),
        ],
        anomaly_results=[],
        overall_score=score,
        execution_time_ms=42.0,
    )


class TestTrendStore:
    """Tests for the TrendStore class."""

    def test_save_and_retrieve(self, tmp_path: Path) -> None:
        """Save a report and retrieve it from history."""
        db_path = str(tmp_path / "test.db")
        store = TrendStore(db_path)

        report = _make_report()
        row_id = store.save_run(report)
        assert row_id > 0

        history = store.get_history("test_suite")
        assert len(history) == 1
        assert history[0]["run_id"] == "abc12345"
        assert history[0]["overall_score"] == 85.0

    def test_get_run_detail(self, tmp_path: Path) -> None:
        """Retrieve full details of a specific run."""
        db_path = str(tmp_path / "test.db")
        store = TrendStore(db_path)

        report = _make_report()
        store.save_run(report)

        detail = store.get_run_detail("abc12345")
        assert detail is not None
        assert detail["suite_name"] == "test_suite"
        assert len(detail["check_results"]) == 1

    def test_score_trend(self, tmp_path: Path) -> None:
        """Score trend returns chronologically ordered data."""
        db_path = str(tmp_path / "test.db")
        store = TrendStore(db_path)

        for i, score in enumerate([70.0, 80.0, 90.0]):
            report = _make_report(score=score)
            report.run_id = f"run_{i:04d}"
            report.timestamp = datetime.datetime(2024, 1, i + 1)
            store.save_run(report)

        trend = store.get_score_trend("test_suite")
        assert len(trend) == 3
        scores = [t["overall_score"] for t in trend]
        assert scores == [70.0, 80.0, 90.0]

    def test_empty_history(self, tmp_path: Path) -> None:
        """Querying nonexistent suite returns empty list."""
        db_path = str(tmp_path / "test.db")
        store = TrendStore(db_path)
        assert store.get_history("nonexistent") == []

    def test_delete_old_runs(self, tmp_path: Path) -> None:
        """Old runs are pruned, keeping only the latest N."""
        db_path = str(tmp_path / "test.db")
        store = TrendStore(db_path)

        for i in range(10):
            report = _make_report()
            report.run_id = f"run_{i:04d}"
            report.timestamp = datetime.datetime(2024, 1, i + 1)
            store.save_run(report)

        deleted = store.delete_old_runs("test_suite", keep_latest=3)
        assert deleted == 7
        remaining = store.get_history("test_suite")
        assert len(remaining) == 3
