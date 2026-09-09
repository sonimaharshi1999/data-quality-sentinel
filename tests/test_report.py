# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Tests for report generation (HTML and console).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.models import (
    CheckResult,
    CheckType,
    Severity,
    ValidationReport,
)
from sentinel.report import generate_console_report, generate_html_report


def _make_report() -> ValidationReport:
    """Helper to create a sample ValidationReport."""
    return ValidationReport(
        suite_name="report_test_suite",
        data_source="test_source",
        run_id="rpt12345",
        total_checks=5,
        passed_checks=3,
        failed_checks=2,
        warning_checks=1,
        critical_failures=1,
        check_results=[
            CheckResult(
                check_name="null_check",
                check_type=CheckType.NOT_NULL,
                column="col_a",
                passed=True,
                severity=Severity.CRITICAL,
                message="No nulls found",
                rows_checked=100,
                rows_failed=0,
                execution_time_ms=1.5,
            ),
            CheckResult(
                check_name="range_check",
                check_type=CheckType.VALUE_RANGE,
                column="col_b",
                passed=False,
                severity=Severity.CRITICAL,
                message="5 values out of range",
                rows_checked=100,
                rows_failed=5,
                execution_time_ms=2.0,
            ),
            CheckResult(
                check_name="pattern_check",
                check_type=CheckType.REGEX_MATCH,
                column="col_c",
                passed=False,
                severity=Severity.WARNING,
                message="3 values don't match pattern",
                rows_checked=100,
                rows_failed=3,
                execution_time_ms=1.8,
            ),
        ],
        anomaly_results=[],
        overall_score=60.0,
        execution_time_ms=15.0,
    )


class TestHTMLReport:
    """Tests for HTML report generation."""

    def test_generates_html_file(self, tmp_path: Path) -> None:
        """HTML report is written to the specified path."""
        report = _make_report()
        template_dir = str(
            Path(__file__).resolve().parent.parent / "templates"
        )
        output = str(tmp_path / "report.html")
        path = generate_html_report(
            report, output_path=output, template_dir=template_dir
        )
        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "report_test_suite" in content
        assert "rpt12345" in content

    def test_html_contains_check_results(self, tmp_path: Path) -> None:
        """HTML report contains check result details."""
        report = _make_report()
        template_dir = str(
            Path(__file__).resolve().parent.parent / "templates"
        )
        output = str(tmp_path / "report.html")
        generate_html_report(report, output_path=output, template_dir=template_dir)
        content = Path(output).read_text(encoding="utf-8")
        assert "null_check" in content
        assert "range_check" in content
        assert "FAIL" in content
        assert "PASS" in content

    def test_html_contains_score(self, tmp_path: Path) -> None:
        """HTML report displays the overall quality score."""
        report = _make_report()
        template_dir = str(
            Path(__file__).resolve().parent.parent / "templates"
        )
        output = str(tmp_path / "report.html")
        generate_html_report(report, output_path=output, template_dir=template_dir)
        content = Path(output).read_text(encoding="utf-8")
        assert "60.0%" in content


class TestConsoleReport:
    """Tests for console text report generation."""

    def test_console_report_contains_summary(self) -> None:
        """Console report includes key summary information."""
        report = _make_report()
        text = generate_console_report(report)
        assert "report_test_suite" in text
        assert "FAILED" in text
        assert "60.0%" in text
        assert "rpt12345" in text

    def test_console_report_lists_checks(self) -> None:
        """Console report lists all check results."""
        report = _make_report()
        text = generate_console_report(report)
        assert "[PASS]" in text
        assert "[FAIL]" in text
        assert "null_check" in text
        assert "range_check" in text
