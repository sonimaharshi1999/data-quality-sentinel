# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Tests for statistical anomaly detection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sentinel.anomaly import detect_anomalies


class TestAnomalyDetection:
    """Tests for the anomaly detection module."""

    def test_normal_data_no_anomaly(self) -> None:
        """Normally distributed data should not trigger anomalies."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame({
            "metric": rng.normal(100, 10, 500),
        })
        results = detect_anomalies(df, columns=["metric"])
        # KS normality test should not flag truly normal data
        ks_results = [r for r in results if r.statistic == "ks_normal"]
        assert len(ks_results) == 1
        assert ks_results[0].is_anomaly is False

    def test_skewed_data_detected(self) -> None:
        """Highly skewed data should be flagged as non-normal."""
        rng = np.random.default_rng(42)
        # Exponential is significantly non-normal
        df = pd.DataFrame({
            "metric": rng.exponential(50, 500),
        })
        results = detect_anomalies(df, columns=["metric"])
        ks_results = [r for r in results if r.statistic == "ks_normal"]
        assert len(ks_results) == 1
        assert ks_results[0].is_anomaly is True

    def test_distribution_shift_detected(self) -> None:
        """Two-sample KS test detects distribution shift."""
        rng = np.random.default_rng(42)
        reference = pd.DataFrame({"value": rng.normal(100, 10, 500)})
        current = pd.DataFrame({"value": rng.normal(130, 10, 500)})  # shifted mean

        results = detect_anomalies(current, columns=["value"], reference_df=reference)
        ks_results = [r for r in results if r.statistic == "ks_2sample"]
        assert len(ks_results) == 1
        assert ks_results[0].is_anomaly is True

    def test_identical_distributions_stable(self) -> None:
        """Two identical distributions should not be flagged."""
        rng = np.random.default_rng(42)
        data = rng.normal(100, 10, 500)
        reference = pd.DataFrame({"value": data})
        current = pd.DataFrame({"value": data})

        results = detect_anomalies(current, columns=["value"], reference_df=reference)
        ks_results = [r for r in results if r.statistic == "ks_2sample"]
        assert len(ks_results) == 1
        assert ks_results[0].is_anomaly is False

    def test_iqr_outlier_detection(self) -> None:
        """IQR method detects outliers in data with extreme values."""
        rng = np.random.default_rng(42)
        normal_data = rng.normal(100, 10, 100).tolist()
        # Add extreme outliers (>5% of data)
        outliers = [500, 600, 700, 800, 900, 1000]
        data = normal_data + outliers

        df = pd.DataFrame({"value": data})
        results = detect_anomalies(df, columns=["value"])
        iqr_results = [r for r in results if r.statistic == "iqr_outliers"]
        assert len(iqr_results) == 1
        assert iqr_results[0].is_anomaly is True
        assert iqr_results[0].details["outlier_count"] > 0

    def test_insufficient_data_skipped(self) -> None:
        """Columns with too few rows are gracefully skipped."""
        df = pd.DataFrame({"tiny": [1, 2, 3]})
        results = detect_anomalies(df, columns=["tiny"])
        assert len(results) == 1
        assert "insufficient data" in results[0].message

    def test_non_numeric_columns_skipped(self) -> None:
        """Non-numeric columns are excluded when columns=None."""
        df = pd.DataFrame({
            "text": ["a", "b", "c"] * 20,
            "number": list(range(60)),
        })
        results = detect_anomalies(df)
        # Only the numeric column should have results
        result_cols = {r.column for r in results}
        assert "text" not in result_cols
        assert "number" in result_cols
