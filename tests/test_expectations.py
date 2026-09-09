# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Tests for expectations loading and validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sentinel.expectations import load_expectations, validate_expectations
from sentinel.models import CheckType, Severity


class TestLoadExpectations:
    """Tests for loading expectation YAML files."""

    def test_load_valid_yaml(self, sample_expectations_yaml: Path) -> None:
        """Loading a valid YAML produces a correct ExpectationSuite."""
        suite = load_expectations(sample_expectations_yaml)
        assert suite.suite_name == "test_suite"
        assert suite.data_source.name == "test_source"
        assert len(suite.checks) == 6

    def test_load_nonexistent_file(self) -> None:
        """Loading a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_expectations("/nonexistent/path/to/file.yaml")

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        """Loading an invalid YAML structure raises ValueError."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("- just\n- a\n- list\n")
        with pytest.raises(ValueError, match="YAML mapping"):
            load_expectations(bad_yaml)

    def test_check_types_parsed_correctly(self, sample_expectations_yaml: Path) -> None:
        """Check types in YAML are mapped to the correct CheckType enums."""
        suite = load_expectations(sample_expectations_yaml)
        check_types = [c.check_type for c in suite.checks]
        assert CheckType.NOT_NULL in check_types
        assert CheckType.UNIQUE in check_types
        assert CheckType.VALUE_RANGE in check_types

    def test_severity_parsed_correctly(self, sample_expectations_yaml: Path) -> None:
        """Severity levels in YAML are correctly mapped."""
        suite = load_expectations(sample_expectations_yaml)
        severities = {c.name: c.severity for c in suite.checks}
        assert severities["id_not_null"] == Severity.CRITICAL
        assert severities["amount_range"] == Severity.WARNING

    def test_invalid_check_type(self, tmp_path: Path) -> None:
        """Unknown check type in YAML raises ValueError."""
        data = {
            "suite_name": "test",
            "data_source": {"name": "test", "path": "test.csv"},
            "checks": [
                {"name": "bad", "check_type": "nonexistent_type"},
            ],
        }
        yaml_path = tmp_path / "bad_check.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(data, f)
        with pytest.raises(ValueError, match="Unknown check_type"):
            load_expectations(yaml_path)


class TestValidateExpectations:
    """Tests for expectation suite validation."""

    def test_valid_suite(self, sample_expectations_yaml: Path) -> None:
        """A valid suite produces no validation errors."""
        suite = load_expectations(sample_expectations_yaml)
        errors = validate_expectations(suite)
        assert len(errors) == 0

    def test_missing_column_for_not_null(self, tmp_path: Path) -> None:
        """Checks requiring a column flag error when column is missing."""
        data = {
            "suite_name": "test",
            "data_source": {"name": "test", "path": "test.csv"},
            "checks": [
                {"name": "bad", "check_type": "not_null", "severity": "critical"},
            ],
        }
        yaml_path = tmp_path / "no_col.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(data, f)
        suite = load_expectations(yaml_path)
        errors = validate_expectations(suite)
        assert any("requires a 'column'" in e for e in errors)

    def test_empty_checks(self, tmp_path: Path) -> None:
        """Suite with no checks produces a validation error."""
        data = {
            "suite_name": "empty",
            "data_source": {"name": "test", "path": "test.csv"},
            "checks": [],
        }
        yaml_path = tmp_path / "empty.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(data, f)
        suite = load_expectations(yaml_path)
        errors = validate_expectations(suite)
        assert any("no checks" in e for e in errors)
