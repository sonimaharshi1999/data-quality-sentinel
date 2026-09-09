# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Validation engine: orchestrates loading data, running checks, detecting
anomalies, and assembling the ValidationReport.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd

from sentinel.anomaly import detect_anomalies
from sentinel.checks import get_registry
from sentinel.models import (
    AnomalyResult,
    CheckResult,
    ExpectationSuite,
    Severity,
    ValidationReport,
)


def load_dataframe(path: str, fmt: str = "csv") -> pd.DataFrame:
    """Load a DataFrame from a file path.

    Args:
        path: File path to load.
        fmt: File format (csv, parquet, json).

    Returns:
        Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the format is unsupported.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    if fmt == "csv":
        return pd.read_csv(path)
    elif fmt == "parquet":
        return pd.read_parquet(path)
    elif fmt == "json":
        return pd.read_json(path)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def run_validation(
    suite: ExpectationSuite,
    df: Optional[pd.DataFrame] = None,
    run_anomaly_detection: bool = True,
    anomaly_columns: Optional[list[str]] = None,
    reference_df: Optional[pd.DataFrame] = None,
) -> ValidationReport:
    """Execute all checks in an expectation suite against a DataFrame.

    Args:
        suite: The expectation suite to run.
        df: DataFrame to validate. If None, loads from suite.data_source.
        run_anomaly_detection: Whether to run statistical anomaly detection.
        anomaly_columns: Specific columns for anomaly detection.
        reference_df: Reference DataFrame for distribution comparison.

    Returns:
        Complete ValidationReport with check results and anomalies.
    """
    start_time = time.time()
    run_id = str(uuid.uuid4())[:8]

    # Load data if not provided
    if df is None:
        df = load_dataframe(suite.data_source.path, suite.data_source.format)

    registry = get_registry()
    check_results: list[CheckResult] = []
    anomaly_results: list[AnomalyResult] = []

    # Execute each check
    for check in suite.checks:
        check_start = time.time()
        try:
            executor = registry.get_executor(check.check_type)
            result = executor(df, check)
            result.execution_time_ms = round((time.time() - check_start) * 1000, 2)
        except Exception as e:
            result = CheckResult(
                check_name=check.name,
                check_type=check.check_type,
                column=check.column,
                passed=False,
                severity=check.severity,
                message=f"Check execution error: {str(e)}",
                execution_time_ms=round((time.time() - check_start) * 1000, 2),
            )
        check_results.append(result)

    # Run anomaly detection
    if run_anomaly_detection:
        try:
            anomaly_results = detect_anomalies(
                df,
                columns=anomaly_columns,
                reference_df=reference_df,
            )
        except Exception as e:
            anomaly_results = [AnomalyResult(
                column="<all>",
                statistic="error",
                p_value=0.0,
                is_anomaly=False,
                message=f"Anomaly detection error: {str(e)}",
            )]

    # Compute summary statistics
    total = len(check_results)
    passed = sum(1 for r in check_results if r.passed)
    failed = total - passed
    warnings = sum(
        1 for r in check_results
        if not r.passed and r.severity == Severity.WARNING
    )
    critical = sum(
        1 for r in check_results
        if not r.passed and r.severity == Severity.CRITICAL
    )

    score = (passed / total * 100) if total > 0 else 100.0
    execution_time = round((time.time() - start_time) * 1000, 2)

    return ValidationReport(
        suite_name=suite.suite_name,
        data_source=suite.data_source.name,
        run_id=run_id,
        total_checks=total,
        passed_checks=passed,
        failed_checks=failed,
        warning_checks=warnings,
        critical_failures=critical,
        check_results=check_results,
        anomaly_results=anomaly_results,
        overall_score=round(score, 2),
        execution_time_ms=execution_time,
    )
