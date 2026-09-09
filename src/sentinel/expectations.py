# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
YAML expectations loader and validator. Parses expectation suite files
into structured Pydantic models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from sentinel.models import (
    CheckType,
    DataSource,
    ExpectationCheck,
    ExpectationSuite,
    Severity,
)


def load_expectations(path: Union[str, Path]) -> ExpectationSuite:
    """Load an expectation suite from a YAML file.

    Args:
        path: Path to the YAML expectations file.

    Returns:
        Parsed ExpectationSuite model.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        ValueError: If the YAML structure is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Expectations file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"Expectations file must be a YAML mapping, got {type(raw).__name__}")

    return _parse_suite(raw, base_dir=path.parent)


def _parse_suite(raw: dict, base_dir: Path) -> ExpectationSuite:
    """Parse raw YAML dict into an ExpectationSuite.

    Args:
        raw: Raw parsed YAML dictionary.
        base_dir: Base directory for resolving relative paths.

    Returns:
        Populated ExpectationSuite.
    """
    suite_name = raw.get("suite_name", "unnamed_suite")
    description = raw.get("description")

    # Parse data source
    ds_raw = raw.get("data_source", {})
    ds_path = ds_raw.get("path", "")
    # Resolve relative paths against the YAML file's directory
    if ds_path and not Path(ds_path).is_absolute():
        ds_path = str(base_dir / ds_path)

    data_source = DataSource(
        name=ds_raw.get("name", "unnamed_source"),
        path=ds_path,
        format=ds_raw.get("format", "csv"),
    )

    # Parse checks
    checks: list[ExpectationCheck] = []
    for check_raw in raw.get("checks", []):
        check = _parse_check(check_raw)
        checks.append(check)

    return ExpectationSuite(
        suite_name=suite_name,
        description=description,
        data_source=data_source,
        checks=checks,
    )


def _parse_check(raw: dict) -> ExpectationCheck:
    """Parse a single check definition from YAML.

    Args:
        raw: Raw check dictionary from YAML.

    Returns:
        Parsed ExpectationCheck.
    """
    check_type_str = raw.get("check_type", "")
    try:
        check_type = CheckType(check_type_str)
    except ValueError:
        valid = [ct.value for ct in CheckType]
        raise ValueError(
            f"Unknown check_type '{check_type_str}'. Valid types: {valid}"
        )

    severity_str = raw.get("severity", "warning")
    try:
        severity = Severity(severity_str)
    except ValueError:
        severity = Severity.WARNING

    return ExpectationCheck(
        name=raw.get("name", f"{check_type_str}_check"),
        check_type=check_type,
        column=raw.get("column"),
        severity=severity,
        params=raw.get("params", {}),
        description=raw.get("description"),
    )


def validate_expectations(suite: ExpectationSuite) -> list[str]:
    """Validate an expectation suite for common configuration errors.

    Args:
        suite: The expectation suite to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []

    if not suite.checks:
        errors.append("Expectation suite has no checks defined")

    column_required_types = {
        CheckType.NOT_NULL, CheckType.UNIQUE, CheckType.VALUE_RANGE,
        CheckType.REGEX_MATCH, CheckType.ALLOWED_VALUES,
        CheckType.MIN_LENGTH, CheckType.MAX_LENGTH,
    }

    for i, check in enumerate(suite.checks):
        if check.check_type in column_required_types and not check.column:
            errors.append(
                f"Check #{i + 1} '{check.name}': check_type '{check.check_type.value}' "
                f"requires a 'column' field"
            )

        if check.check_type == CheckType.VALUE_RANGE:
            if "min" not in check.params and "max" not in check.params:
                errors.append(
                    f"Check #{i + 1} '{check.name}': value_range requires "
                    f"at least 'min' or 'max' in params"
                )

        if check.check_type == CheckType.REGEX_MATCH:
            if "pattern" not in check.params:
                errors.append(
                    f"Check #{i + 1} '{check.name}': regex_match requires "
                    f"'pattern' in params"
                )

        if check.check_type == CheckType.ALLOWED_VALUES:
            if "values" not in check.params:
                errors.append(
                    f"Check #{i + 1} '{check.name}': allowed_values requires "
                    f"'values' in params"
                )

        if check.check_type == CheckType.ROW_COUNT:
            if "min" not in check.params and "max" not in check.params:
                errors.append(
                    f"Check #{i + 1} '{check.name}': row_count requires "
                    f"at least 'min' or 'max' in params"
                )

    return errors
