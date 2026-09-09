# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Built-in validation check executors. Each check takes a DataFrame and
an ExpectationCheck, returning a CheckResult.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from sentinel.checks.registry import _registry
from sentinel.models import CheckResult, CheckType, ExpectationCheck


def _make_result(
    check: ExpectationCheck,
    passed: bool,
    message: str,
    rows_checked: int = 0,
    rows_failed: int = 0,
    details: dict[str, Any] | None = None,
) -> CheckResult:
    """Helper to construct a CheckResult from common fields.

    Args:
        check: The expectation check definition.
        passed: Whether the check passed.
        message: Human-readable result message.
        rows_checked: Total rows examined.
        rows_failed: Rows that failed the check.
        details: Additional detail dictionary.

    Returns:
        Populated CheckResult.
    """
    return CheckResult(
        check_name=check.name,
        check_type=check.check_type,
        column=check.column,
        passed=passed,
        severity=check.severity,
        message=message,
        details=details or {},
        rows_checked=rows_checked,
        rows_failed=rows_failed,
    )


# ---------------------------------------------------------------------------
# NOT NULL CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.NOT_NULL)
def check_not_null(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that a column has no null values (or null rate below threshold).

    Params:
        threshold (float): Maximum allowed null rate (0.0 to 1.0). Default 0.0.
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    total = len(df)
    null_count = int(df[col].isna().sum())
    null_rate = null_count / total if total > 0 else 0.0
    threshold = float(check.params.get("threshold", 0.0))

    passed = null_rate <= threshold
    msg = (
        f"Column '{col}': null_rate={null_rate:.4f} "
        f"({'<=' if passed else '>'} threshold={threshold:.4f})"
    )
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=null_count,
        details={"null_count": null_count, "null_rate": round(null_rate, 6), "threshold": threshold},
    )


# ---------------------------------------------------------------------------
# UNIQUE CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.UNIQUE)
def check_unique(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that a column contains only unique values.

    Params:
        threshold (float): Maximum allowed duplicate rate. Default 0.0.
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    total = len(df)
    dup_count = int(df[col].duplicated(keep=False).sum())
    dup_rate = dup_count / total if total > 0 else 0.0
    threshold = float(check.params.get("threshold", 0.0))

    passed = dup_rate <= threshold
    msg = (
        f"Column '{col}': duplicate_rate={dup_rate:.4f} "
        f"({'<=' if passed else '>'} threshold={threshold:.4f})"
    )
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=dup_count,
        details={"duplicate_count": dup_count, "duplicate_rate": round(dup_rate, 6)},
    )


# ---------------------------------------------------------------------------
# VALUE RANGE CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.VALUE_RANGE)
def check_value_range(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that numeric column values fall within [min, max].

    Params:
        min (float): Minimum allowed value (inclusive).
        max (float): Maximum allowed value (inclusive).
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    series = pd.to_numeric(df[col], errors="coerce")
    total = int(series.notna().sum())
    min_val = check.params.get("min")
    max_val = check.params.get("max")

    mask = pd.Series([True] * len(df), index=df.index)
    if min_val is not None:
        mask &= series >= float(min_val)
    if max_val is not None:
        mask &= series <= float(max_val)
    # Only count non-null rows
    mask &= series.notna()

    failed = int((~mask & series.notna()).sum())
    passed = failed == 0

    range_str = f"[{min_val}, {max_val}]"
    msg = f"Column '{col}': {failed} of {total} values outside range {range_str}"
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=failed,
        details={"min_param": min_val, "max_param": max_val,
                 "actual_min": float(series.min()) if total > 0 else None,
                 "actual_max": float(series.max()) if total > 0 else None},
    )


# ---------------------------------------------------------------------------
# REGEX MATCH CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.REGEX_MATCH)
def check_regex_match(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that string column values match a regex pattern.

    Params:
        pattern (str): Regular expression pattern.
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    pattern = check.params.get("pattern", "")
    series = df[col].dropna().astype(str)
    total = len(series)
    matches = series.str.match(pattern, na=False)
    failed = int((~matches).sum())
    passed = failed == 0

    msg = f"Column '{col}': {failed} of {total} values don't match pattern '{pattern}'"
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=failed,
        details={"pattern": pattern},
    )


# ---------------------------------------------------------------------------
# ALLOWED VALUES CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.ALLOWED_VALUES)
def check_allowed_values(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that column values are within an allowed set.

    Params:
        values (list): List of allowed values.
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    allowed = set(check.params.get("values", []))
    series = df[col].dropna()
    total = len(series)
    invalid_mask = ~series.isin(allowed)
    failed = int(invalid_mask.sum())
    passed = failed == 0

    unexpected = sorted(series[invalid_mask].unique().tolist())[:10]
    msg = f"Column '{col}': {failed} values not in allowed set"
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=failed,
        details={"allowed_values": sorted(allowed), "unexpected_sample": unexpected},
    )


# ---------------------------------------------------------------------------
# MIN LENGTH CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.MIN_LENGTH)
def check_min_length(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that string column values meet minimum length.

    Params:
        length (int): Minimum string length.
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    min_len = int(check.params.get("length", 1))
    series = df[col].dropna().astype(str)
    total = len(series)
    lengths = series.str.len()
    failed = int((lengths < min_len).sum())
    passed = failed == 0

    msg = f"Column '{col}': {failed} of {total} values shorter than {min_len} chars"
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=failed,
        details={"min_length": min_len, "shortest_found": int(lengths.min()) if total > 0 else None},
    )


# ---------------------------------------------------------------------------
# MAX LENGTH CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.MAX_LENGTH)
def check_max_length(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that string column values do not exceed maximum length.

    Params:
        length (int): Maximum string length.
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    max_len = int(check.params.get("length", 255))
    series = df[col].dropna().astype(str)
    total = len(series)
    lengths = series.str.len()
    failed = int((lengths > max_len).sum())
    passed = failed == 0

    msg = f"Column '{col}': {failed} of {total} values longer than {max_len} chars"
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=failed,
        details={"max_length": max_len, "longest_found": int(lengths.max()) if total > 0 else None},
    )


# ---------------------------------------------------------------------------
# REFERENTIAL INTEGRITY CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.REFERENTIAL_INTEGRITY)
def check_referential_integrity(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that column values exist in a reference dataset.

    Params:
        reference_path (str): Path to reference CSV file.
        reference_column (str): Column name in reference file.
    """
    col = check.column
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    ref_path = check.params.get("reference_path", "")
    ref_col = check.params.get("reference_column", col)

    if not ref_path or not Path(ref_path).exists():
        return _make_result(
            check, False,
            f"Reference file not found: {ref_path}",
            details={"reference_path": ref_path},
        )

    ref_df = pd.read_csv(ref_path)
    if ref_col not in ref_df.columns:
        return _make_result(
            check, False,
            f"Reference column '{ref_col}' not found in {ref_path}",
        )

    ref_values = set(ref_df[ref_col].dropna().unique())
    series = df[col].dropna()
    total = len(series)
    missing_mask = ~series.isin(ref_values)
    failed = int(missing_mask.sum())
    passed = failed == 0

    orphan_sample = sorted(series[missing_mask].unique().tolist())[:10]
    msg = f"Column '{col}': {failed} of {total} values not found in reference"
    return _make_result(
        check, passed, msg,
        rows_checked=total, rows_failed=failed,
        details={"reference_path": ref_path, "reference_column": ref_col,
                 "orphan_sample": orphan_sample},
    )


# ---------------------------------------------------------------------------
# FRESHNESS CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.FRESHNESS)
def check_freshness(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that the most recent timestamp is within a freshness window.

    Params:
        column (str): Timestamp column name (overrides check.column).
        max_age_hours (float): Maximum allowed age in hours.
    """
    col = check.column or check.params.get("column", "")
    if col not in df.columns:
        return _make_result(check, False, f"Column '{col}' not found in dataset")

    max_age_hours = float(check.params.get("max_age_hours", 24))
    series = pd.to_datetime(df[col], errors="coerce")
    valid = series.dropna()

    if len(valid) == 0:
        return _make_result(check, False, f"Column '{col}': no valid timestamps found")

    most_recent = valid.max()
    now = datetime.utcnow()
    age = now - most_recent.to_pydatetime()
    age_hours = age.total_seconds() / 3600

    passed = age_hours <= max_age_hours
    msg = (
        f"Column '{col}': most recent={most_recent}, "
        f"age={age_hours:.1f}h ({'<=' if passed else '>'} {max_age_hours}h)"
    )
    return _make_result(
        check, passed, msg,
        rows_checked=len(valid),
        details={"most_recent": str(most_recent), "age_hours": round(age_hours, 2),
                 "max_age_hours": max_age_hours},
    )


# ---------------------------------------------------------------------------
# ROW COUNT CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.ROW_COUNT)
def check_row_count(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that row count falls within expected range.

    Params:
        min (int): Minimum expected row count.
        max (int): Maximum expected row count.
    """
    total = len(df)
    min_rows = check.params.get("min")
    max_rows = check.params.get("max")

    passed = True
    if min_rows is not None and total < int(min_rows):
        passed = False
    if max_rows is not None and total > int(max_rows):
        passed = False

    msg = f"Row count: {total} (expected [{min_rows}, {max_rows}])"
    return _make_result(
        check, passed, msg,
        rows_checked=total,
        details={"row_count": total, "min_expected": min_rows, "max_expected": max_rows},
    )


# ---------------------------------------------------------------------------
# COLUMN EXISTS CHECK
# ---------------------------------------------------------------------------
@_registry.register(CheckType.COLUMN_EXISTS)
def check_column_exists(df: pd.DataFrame, check: ExpectationCheck) -> CheckResult:
    """Validate that expected columns exist in the dataset.

    Params:
        columns (list[str]): List of column names that must exist.
            If not provided, uses check.column as a single column to verify.
    """
    expected_cols = check.params.get("columns", [])
    if not expected_cols and check.column:
        expected_cols = [check.column]

    actual_cols = set(df.columns.tolist())
    missing = [c for c in expected_cols if c not in actual_cols]

    passed = len(missing) == 0
    msg = (
        f"All {len(expected_cols)} expected columns present"
        if passed
        else f"Missing columns: {missing}"
    )
    return _make_result(
        check, passed, msg,
        details={"expected": expected_cols, "missing": missing,
                 "actual_columns": sorted(actual_cols)},
    )
