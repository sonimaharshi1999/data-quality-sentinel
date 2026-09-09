# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Tests for built-in validation checks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sentinel.checks import get_registry
from sentinel.models import CheckType, ExpectationCheck, Severity


class TestNotNullCheck:
    """Tests for the not_null check type."""

    def test_passes_clean_data(self, sample_df: pd.DataFrame) -> None:
        """Not-null check passes when column has no nulls."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_not_null",
            check_type=CheckType.NOT_NULL,
            column="id",
            severity=Severity.CRITICAL,
        )
        result = registry.get_executor(CheckType.NOT_NULL)(sample_df, check)
        assert result.passed is True
        assert result.rows_failed == 0

    def test_fails_with_nulls(self, dirty_df: pd.DataFrame) -> None:
        """Not-null check fails when column has null values."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_not_null",
            check_type=CheckType.NOT_NULL,
            column="email",
            severity=Severity.WARNING,
        )
        result = registry.get_executor(CheckType.NOT_NULL)(dirty_df, check)
        assert result.passed is False
        assert result.rows_failed == 3  # 3 nulls injected

    def test_threshold_allows_some_nulls(self, dirty_df: pd.DataFrame) -> None:
        """Not-null check passes when null rate is below threshold."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_not_null_threshold",
            check_type=CheckType.NOT_NULL,
            column="email",
            severity=Severity.WARNING,
            params={"threshold": 0.05},  # 5% threshold, ~3% nulls
        )
        result = registry.get_executor(CheckType.NOT_NULL)(dirty_df, check)
        assert result.passed is True

    def test_missing_column(self, sample_df: pd.DataFrame) -> None:
        """Not-null check fails when column doesn't exist."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_missing",
            check_type=CheckType.NOT_NULL,
            column="nonexistent",
            severity=Severity.CRITICAL,
        )
        result = registry.get_executor(CheckType.NOT_NULL)(sample_df, check)
        assert result.passed is False
        assert "not found" in result.message


class TestUniqueCheck:
    """Tests for the unique check type."""

    def test_passes_unique_column(self, sample_df: pd.DataFrame) -> None:
        """Unique check passes for fully unique column."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_unique",
            check_type=CheckType.UNIQUE,
            column="id",
            severity=Severity.CRITICAL,
        )
        result = registry.get_executor(CheckType.UNIQUE)(sample_df, check)
        assert result.passed is True

    def test_fails_with_duplicates(self, dirty_df: pd.DataFrame) -> None:
        """Unique check fails when column has duplicates."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_unique",
            check_type=CheckType.UNIQUE,
            column="id",
            severity=Severity.CRITICAL,
        )
        result = registry.get_executor(CheckType.UNIQUE)(dirty_df, check)
        assert result.passed is False
        assert result.rows_failed > 0


class TestValueRangeCheck:
    """Tests for the value_range check type."""

    def test_passes_in_range(self, sample_df: pd.DataFrame) -> None:
        """Range check passes when all values within bounds."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_range",
            check_type=CheckType.VALUE_RANGE,
            column="amount",
            severity=Severity.WARNING,
            params={"min": 0, "max": 1000},
        )
        result = registry.get_executor(CheckType.VALUE_RANGE)(sample_df, check)
        assert result.passed is True

    def test_fails_out_of_range(self, dirty_df: pd.DataFrame) -> None:
        """Range check fails when values are outside bounds."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_range",
            check_type=CheckType.VALUE_RANGE,
            column="amount",
            severity=Severity.CRITICAL,
            params={"min": 0, "max": 1000},
        )
        result = registry.get_executor(CheckType.VALUE_RANGE)(dirty_df, check)
        assert result.passed is False
        assert result.rows_failed >= 2  # 2 negatives injected


class TestRegexMatchCheck:
    """Tests for the regex_match check type."""

    def test_passes_valid_emails(self, sample_df: pd.DataFrame) -> None:
        """Regex check passes when all values match pattern."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_regex",
            check_type=CheckType.REGEX_MATCH,
            column="email",
            severity=Severity.WARNING,
            params={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
        )
        result = registry.get_executor(CheckType.REGEX_MATCH)(sample_df, check)
        assert result.passed is True

    def test_fails_invalid_emails(self, dirty_df: pd.DataFrame) -> None:
        """Regex check fails when values don't match pattern."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_regex",
            check_type=CheckType.REGEX_MATCH,
            column="email",
            severity=Severity.WARNING,
            params={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
        )
        result = registry.get_executor(CheckType.REGEX_MATCH)(dirty_df, check)
        assert result.passed is False
        assert result.rows_failed >= 2


class TestAllowedValuesCheck:
    """Tests for the allowed_values check type."""

    def test_passes_valid_values(self, sample_df: pd.DataFrame) -> None:
        """Allowed values check passes with valid set."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_allowed",
            check_type=CheckType.ALLOWED_VALUES,
            column="status",
            severity=Severity.WARNING,
            params={"values": ["active", "inactive", "pending"]},
        )
        result = registry.get_executor(CheckType.ALLOWED_VALUES)(sample_df, check)
        assert result.passed is True

    def test_fails_invalid_values(self, dirty_df: pd.DataFrame) -> None:
        """Allowed values check fails with unexpected values."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_allowed",
            check_type=CheckType.ALLOWED_VALUES,
            column="status",
            severity=Severity.WARNING,
            params={"values": ["active", "inactive", "pending"]},
        )
        result = registry.get_executor(CheckType.ALLOWED_VALUES)(dirty_df, check)
        assert result.passed is False
        assert "INVALID" in str(result.details.get("unexpected_sample", []))


class TestRowCountCheck:
    """Tests for the row_count check type."""

    def test_passes_within_range(self, sample_df: pd.DataFrame) -> None:
        """Row count check passes when count is in range."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_row_count",
            check_type=CheckType.ROW_COUNT,
            severity=Severity.CRITICAL,
            params={"min": 50, "max": 200},
        )
        result = registry.get_executor(CheckType.ROW_COUNT)(sample_df, check)
        assert result.passed is True

    def test_fails_below_minimum(self, sample_df: pd.DataFrame) -> None:
        """Row count check fails when below minimum."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_row_count",
            check_type=CheckType.ROW_COUNT,
            severity=Severity.CRITICAL,
            params={"min": 500},
        )
        result = registry.get_executor(CheckType.ROW_COUNT)(sample_df, check)
        assert result.passed is False


class TestColumnExistsCheck:
    """Tests for the column_exists check type."""

    def test_passes_all_exist(self, sample_df: pd.DataFrame) -> None:
        """Column exists check passes when all columns present."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_cols_exist",
            check_type=CheckType.COLUMN_EXISTS,
            severity=Severity.CRITICAL,
            params={"columns": ["id", "name", "amount"]},
        )
        result = registry.get_executor(CheckType.COLUMN_EXISTS)(sample_df, check)
        assert result.passed is True

    def test_fails_missing_columns(self, sample_df: pd.DataFrame) -> None:
        """Column exists check fails when columns are missing."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_cols_exist",
            check_type=CheckType.COLUMN_EXISTS,
            severity=Severity.CRITICAL,
            params={"columns": ["id", "nonexistent_col"]},
        )
        result = registry.get_executor(CheckType.COLUMN_EXISTS)(sample_df, check)
        assert result.passed is False
        assert "nonexistent_col" in result.details["missing"]


class TestLengthChecks:
    """Tests for min_length and max_length checks."""

    def test_min_length_passes(self, sample_df: pd.DataFrame) -> None:
        """Min length passes when values meet minimum."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_min_len",
            check_type=CheckType.MIN_LENGTH,
            column="id",
            severity=Severity.WARNING,
            params={"length": 5},
        )
        result = registry.get_executor(CheckType.MIN_LENGTH)(sample_df, check)
        assert result.passed is True

    def test_max_length_passes(self, sample_df: pd.DataFrame) -> None:
        """Max length passes when values are within limit."""
        registry = get_registry()
        check = ExpectationCheck(
            name="test_max_len",
            check_type=CheckType.MAX_LENGTH,
            column="email",
            severity=Severity.WARNING,
            params={"length": 100},
        )
        result = registry.get_executor(CheckType.MAX_LENGTH)(sample_df, check)
        assert result.passed is True
