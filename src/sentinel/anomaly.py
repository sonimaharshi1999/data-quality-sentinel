# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Statistical anomaly detection on column distributions.
Uses the Kolmogorov-Smirnov test to compare current data distributions
against a reference (uniform or normal) to detect drift and outliers.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from sentinel.models import AnomalyResult


def detect_anomalies(
    df: pd.DataFrame,
    columns: Optional[list[str]] = None,
    p_value_threshold: float = 0.05,
    reference_df: Optional[pd.DataFrame] = None,
) -> list[AnomalyResult]:
    """Run anomaly detection on numeric columns of a DataFrame.

    For each numeric column, performs a Kolmogorov-Smirnov test against
    either a reference distribution or a fitted normal distribution.

    Args:
        df: Current DataFrame to analyze.
        columns: Specific columns to check. If None, checks all numeric columns.
        p_value_threshold: Significance level for anomaly detection.
        reference_df: Optional reference DataFrame for two-sample KS test.

    Returns:
        List of AnomalyResult for each analyzed column.
    """
    results: list[AnomalyResult] = []

    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in columns:
        if col not in df.columns:
            continue

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(series) < 10:
            results.append(AnomalyResult(
                column=col,
                statistic="ks_test",
                p_value=1.0,
                is_anomaly=False,
                message=f"Column '{col}': insufficient data ({len(series)} rows) for anomaly detection",
                details={"sample_size": len(series)},
            ))
            continue

        if reference_df is not None and col in reference_df.columns:
            result = _two_sample_ks_test(col, series, reference_df[col], p_value_threshold)
        else:
            result = _normality_test(col, series, p_value_threshold)

        results.append(result)

        # Also check for outliers using IQR
        outlier_result = _iqr_outlier_check(col, series)
        results.append(outlier_result)

    return results


def _two_sample_ks_test(
    col: str,
    current: pd.Series,
    reference: pd.Series,
    threshold: float,
) -> AnomalyResult:
    """Perform two-sample Kolmogorov-Smirnov test.

    Args:
        col: Column name.
        current: Current data series.
        reference: Reference data series.
        threshold: P-value threshold for significance.

    Returns:
        AnomalyResult with test results.
    """
    ref_clean = pd.to_numeric(reference, errors="coerce").dropna()
    if len(ref_clean) < 10:
        return AnomalyResult(
            column=col,
            statistic="ks_2sample",
            p_value=1.0,
            is_anomaly=False,
            message=f"Column '{col}': insufficient reference data for comparison",
        )

    ks_stat, p_value = stats.ks_2samp(current.values, ref_clean.values)
    is_anomaly = p_value < threshold

    return AnomalyResult(
        column=col,
        statistic="ks_2sample",
        p_value=round(float(p_value), 6),
        is_anomaly=is_anomaly,
        message=(
            f"Column '{col}': distribution {'SHIFTED' if is_anomaly else 'stable'} "
            f"(KS={ks_stat:.4f}, p={p_value:.4f})"
        ),
        details={
            "ks_statistic": round(float(ks_stat), 6),
            "current_mean": round(float(current.mean()), 4),
            "current_std": round(float(current.std()), 4),
            "reference_mean": round(float(ref_clean.mean()), 4),
            "reference_std": round(float(ref_clean.std()), 4),
        },
    )


def _normality_test(
    col: str,
    series: pd.Series,
    threshold: float,
) -> AnomalyResult:
    """Test whether a column's distribution deviates significantly from normal.

    Uses the Kolmogorov-Smirnov test against a fitted normal distribution.

    Args:
        col: Column name.
        series: Data series to test.
        threshold: P-value threshold for significance.

    Returns:
        AnomalyResult with test results.
    """
    mean = float(series.mean())
    std = float(series.std())

    if std == 0:
        return AnomalyResult(
            column=col,
            statistic="ks_normal",
            p_value=1.0,
            is_anomaly=False,
            message=f"Column '{col}': constant values (std=0), skipping normality test",
            details={"mean": mean, "std": 0.0},
        )

    fitted_cdf = stats.norm(loc=mean, scale=std).cdf
    ks_stat, p_value = stats.kstest(series.values, fitted_cdf)
    is_anomaly = p_value < threshold

    skewness = float(stats.skew(series.values))
    kurtosis = float(stats.kurtosis(series.values))

    return AnomalyResult(
        column=col,
        statistic="ks_normal",
        p_value=round(float(p_value), 6),
        is_anomaly=is_anomaly,
        message=(
            f"Column '{col}': distribution {'NON-NORMAL' if is_anomaly else 'approximately normal'} "
            f"(KS={ks_stat:.4f}, p={p_value:.4f})"
        ),
        details={
            "ks_statistic": round(float(ks_stat), 6),
            "mean": round(mean, 4),
            "std": round(std, 4),
            "skewness": round(skewness, 4),
            "kurtosis": round(kurtosis, 4),
        },
    )


def _iqr_outlier_check(col: str, series: pd.Series) -> AnomalyResult:
    """Detect outliers using the Interquartile Range (IQR) method.

    Args:
        col: Column name.
        series: Numeric data series.

    Returns:
        AnomalyResult with outlier count and details.
    """
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    outlier_mask = (series < lower_bound) | (series > upper_bound)
    outlier_count = int(outlier_mask.sum())
    outlier_rate = outlier_count / len(series) if len(series) > 0 else 0.0

    # Flag as anomaly if more than 5% are outliers
    is_anomaly = outlier_rate > 0.05

    return AnomalyResult(
        column=col,
        statistic="iqr_outliers",
        p_value=round(1.0 - outlier_rate, 6),
        is_anomaly=is_anomaly,
        message=(
            f"Column '{col}': {outlier_count} outliers ({outlier_rate:.1%}) "
            f"outside [{lower_bound:.2f}, {upper_bound:.2f}]"
        ),
        details={
            "outlier_count": outlier_count,
            "outlier_rate": round(outlier_rate, 6),
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "lower_bound": round(lower_bound, 4),
            "upper_bound": round(upper_bound, 4),
        },
    )
