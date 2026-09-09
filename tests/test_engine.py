# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Tests for the validation engine.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sentinel.engine import load_dataframe, run_validation
from sentinel.expectations import load_expectations
from sentinel.models import Severity


class TestLoadDataframe:
    """Tests for DataFrame loading."""

    def test_load_csv(self, sample_df: pd.DataFrame, tmp_path: Path) -> None:
        """Load CSV file into a DataFrame."""
        csv_path = tmp_path / "test.csv"
        sample_df.to_csv(csv_path, index=False)
        loaded = load_dataframe(str(csv_path), "csv")
        assert len(loaded) == len(sample_df)
        assert list(loaded.columns) == list(sample_df.columns)

    def test_load_nonexistent_file(self) -> None:
        """Loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_dataframe("/no/such/file.csv")

    def test_load_unsupported_format(self, tmp_path: Path) -> None:
        """Loading unsupported format raises ValueError."""
        f = tmp_path / "test.xyz"
        f.write_text("data")
        with pytest.raises(ValueError, match="Unsupported format"):
            load_dataframe(str(f), "xyz")


class TestRunValidation:
    """Tests for the full validation engine pipeline."""

    def test_clean_data_all_pass(
        self, sample_expectations_yaml: Path, sample_df: pd.DataFrame
    ) -> None:
        """All checks pass on clean data."""
        suite = load_expectations(sample_expectations_yaml)
        report = run_validation(suite, df=sample_df, run_anomaly_detection=False)
        assert report.passed_checks == report.total_checks
        assert report.failed_checks == 0
        assert report.overall_score == 100.0

    def test_dirty_data_has_failures(self, dirty_df: pd.DataFrame, tmp_path: Path) -> None:
        """Validation detects failures in dirty data."""
        import yaml

        csv_path = tmp_path / "dirty.csv"
        dirty_df.to_csv(csv_path, index=False)

        expectations = {
            "suite_name": "dirty_suite",
            "data_source": {"name": "dirty", "path": str(csv_path), "format": "csv"},
            "checks": [
                {"name": "id_unique", "check_type": "unique", "column": "id",
                 "severity": "critical"},
                {"name": "email_not_null", "check_type": "not_null", "column": "email",
                 "severity": "warning"},
                {"name": "amount_range", "check_type": "value_range", "column": "amount",
                 "severity": "critical", "params": {"min": 0, "max": 1000}},
                {"name": "valid_status", "check_type": "allowed_values", "column": "status",
                 "severity": "warning",
                 "params": {"values": ["active", "inactive", "pending"]}},
            ],
        }

        yaml_path = tmp_path / "dirty_expectations.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(expectations, f)

        suite = load_expectations(yaml_path)
        report = run_validation(suite, run_anomaly_detection=False)

        assert report.failed_checks > 0
        assert report.critical_failures > 0
        assert report.overall_score < 100.0
        assert not report.passed

    def test_report_has_run_id(self, sample_expectations_yaml: Path, sample_df: pd.DataFrame) -> None:
        """Report is assigned a unique run ID."""
        suite = load_expectations(sample_expectations_yaml)
        report = run_validation(suite, df=sample_df, run_anomaly_detection=False)
        assert report.run_id is not None
        assert len(report.run_id) == 8

    def test_report_execution_time(
        self, sample_expectations_yaml: Path, sample_df: pd.DataFrame
    ) -> None:
        """Report tracks total execution time."""
        suite = load_expectations(sample_expectations_yaml)
        report = run_validation(suite, df=sample_df, run_anomaly_detection=False)
        assert report.execution_time_ms > 0
