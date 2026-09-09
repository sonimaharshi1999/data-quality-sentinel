# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Shared pytest fixtures for the test suite.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create a clean sample DataFrame for testing."""
    return pd.DataFrame({
        "id": [f"ID-{i:04d}" for i in range(100)],
        "name": [f"Item_{i}" for i in range(100)],
        "email": [f"user{i}@example.com" for i in range(100)],
        "amount": np.random.default_rng(42).uniform(10.0, 500.0, 100).round(2),
        "quantity": np.random.default_rng(42).integers(1, 50, 100),
        "status": np.random.default_rng(42).choice(
            ["active", "inactive", "pending"], 100
        ),
        "created_at": pd.date_range("2024-01-01", periods=100, freq="D").astype(str),
    })


@pytest.fixture
def dirty_df() -> pd.DataFrame:
    """Create a DataFrame with intentional quality issues."""
    rng = np.random.default_rng(99)
    n = 100

    ids = [f"ID-{i:04d}" for i in range(n)]
    # Inject duplicates
    ids[10] = ids[0]
    ids[20] = ids[1]

    emails: list = [f"user{i}@example.com" for i in range(n)]
    # Inject nulls
    emails[5] = None
    emails[15] = None
    emails[25] = None
    # Inject invalid
    emails[30] = "not-an-email"
    emails[31] = "also_bad"

    amounts = rng.uniform(10.0, 500.0, n).round(2).tolist()
    # Inject negatives
    amounts[40] = -50.0
    amounts[41] = -100.0
    # Inject null
    amounts[50] = float("nan")

    quantities = rng.integers(1, 20, n).tolist()
    # Inject outlier
    quantities[60] = 999

    statuses = list(rng.choice(["active", "inactive", "pending"], n))
    statuses[70] = "INVALID"

    return pd.DataFrame({
        "id": ids,
        "email": emails,
        "amount": amounts,
        "quantity": quantities,
        "status": statuses,
    })


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for test outputs."""
    return tmp_path


@pytest.fixture
def sample_expectations_yaml(tmp_path: Path, sample_df: pd.DataFrame) -> Path:
    """Create a temporary expectations YAML file and corresponding CSV."""
    csv_path = tmp_path / "test_data.csv"
    sample_df.to_csv(csv_path, index=False)

    expectations = {
        "suite_name": "test_suite",
        "description": "Test expectation suite",
        "data_source": {
            "name": "test_source",
            "path": str(csv_path),
            "format": "csv",
        },
        "checks": [
            {
                "name": "id_not_null",
                "check_type": "not_null",
                "column": "id",
                "severity": "critical",
            },
            {
                "name": "id_unique",
                "check_type": "unique",
                "column": "id",
                "severity": "critical",
            },
            {
                "name": "amount_range",
                "check_type": "value_range",
                "column": "amount",
                "severity": "warning",
                "params": {"min": 0, "max": 1000},
            },
            {
                "name": "email_pattern",
                "check_type": "regex_match",
                "column": "email",
                "severity": "warning",
                "params": {"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
            },
            {
                "name": "valid_status",
                "check_type": "allowed_values",
                "column": "status",
                "severity": "info",
                "params": {"values": ["active", "inactive", "pending"]},
            },
            {
                "name": "row_count_check",
                "check_type": "row_count",
                "severity": "critical",
                "params": {"min": 50, "max": 500},
            },
        ],
    }

    yaml_path = tmp_path / "test_expectations.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(expectations, f, default_flow_style=False)

    return yaml_path
