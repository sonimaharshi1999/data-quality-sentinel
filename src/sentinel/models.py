# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Pydantic models for validation expectations, check results, and report data.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity level for validation checks."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class CheckType(str, Enum):
    """Supported validation check types."""
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    VALUE_RANGE = "value_range"
    REGEX_MATCH = "regex_match"
    ALLOWED_VALUES = "allowed_values"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    FRESHNESS = "freshness"
    ROW_COUNT = "row_count"
    CUSTOM_SQL = "custom_sql"
    COLUMN_EXISTS = "column_exists"


class ExpectationCheck(BaseModel):
    """A single validation check definition loaded from YAML."""
    name: str = Field(..., description="Human-readable name for the check")
    check_type: CheckType = Field(..., description="Type of validation check")
    column: Optional[str] = Field(None, description="Target column name")
    severity: Severity = Field(Severity.WARNING, description="Severity if check fails")
    params: dict[str, Any] = Field(default_factory=dict, description="Check-specific parameters")
    description: Optional[str] = Field(None, description="Optional description of what this check validates")


class DataSource(BaseModel):
    """Data source configuration from YAML expectations file."""
    name: str = Field(..., description="Name identifier for the data source")
    path: str = Field(..., description="File path to the data source (CSV, Parquet)")
    format: str = Field("csv", description="File format: csv, parquet, json")


class ExpectationSuite(BaseModel):
    """Complete expectations suite loaded from YAML."""
    suite_name: str = Field(..., description="Name of the expectation suite")
    description: Optional[str] = Field(None, description="Suite description")
    data_source: DataSource = Field(..., description="Data source configuration")
    checks: list[ExpectationCheck] = Field(default_factory=list, description="List of validation checks")


class CheckResult(BaseModel):
    """Result of a single validation check execution."""
    check_name: str
    check_type: CheckType
    column: Optional[str] = None
    passed: bool
    severity: Severity
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    rows_checked: int = 0
    rows_failed: int = 0
    execution_time_ms: float = 0.0


class AnomalyResult(BaseModel):
    """Result from statistical anomaly detection on a column."""
    column: str
    statistic: str
    p_value: float
    is_anomaly: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Complete validation report for a single run."""
    suite_name: str
    data_source: str
    run_id: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    critical_failures: int = 0
    check_results: list[CheckResult] = Field(default_factory=list)
    anomaly_results: list[AnomalyResult] = Field(default_factory=list)
    overall_score: float = Field(0.0, description="Quality score 0-100")
    execution_time_ms: float = 0.0

    @property
    def passed(self) -> bool:
        """Report passes if no critical failures exist."""
        return self.critical_failures == 0
