# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Synthetic data generator: creates CSV datasets with intentional quality
issues for testing and demonstration.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


def generate_orders_dataset(
    n_rows: int = 1000,
    output_path: Optional[str] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a synthetic e-commerce orders dataset with quality issues.

    Intentional issues injected:
      - ~3% null values in customer_email
      - ~2% null values in order_total
      - ~5% duplicate order_ids
      - ~2% negative order totals (invalid)
      - ~3% invalid email formats
      - ~1% out-of-range quantities
      - Some orders with future dates

    Args:
        n_rows: Number of rows to generate.
        output_path: If provided, saves the DataFrame as CSV.
        seed: Random seed for reproducibility.

    Returns:
        Generated DataFrame with quality issues.
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    # Base data
    order_ids = [f"ORD-{i:06d}" for i in range(n_rows)]
    # Inject ~5% duplicates
    n_dups = int(n_rows * 0.05)
    for i in rng.choice(n_rows, size=n_dups, replace=False):
        order_ids[i] = order_ids[rng.integers(0, n_rows)]

    # Customer IDs
    customer_ids = [f"CUST-{rng.integers(1, 200):04d}" for _ in range(n_rows)]

    # Emails with ~3% invalid formats
    domains = ["gmail.com", "yahoo.com", "company.com", "outlook.com"]
    first_names = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "hank"]
    emails: list[Optional[str]] = []
    for i in range(n_rows):
        name = random.choice(first_names)
        domain = random.choice(domains)
        email = f"{name}{rng.integers(1,999)}@{domain}"
        # ~3% invalid emails
        if rng.random() < 0.03:
            email = f"invalid-email-{i}"
        # ~3% null emails
        if rng.random() < 0.03:
            email = None
        emails.append(email)

    # Order totals with ~2% negative and ~2% null
    totals: list[Optional[float]] = []
    for _ in range(n_rows):
        val = round(float(rng.exponential(50) + 5), 2)
        if rng.random() < 0.02:
            val = round(-abs(val), 2)
        if rng.random() < 0.02:
            val = None  # type: ignore
        totals.append(val)

    # Quantities with ~1% out of range
    quantities = []
    for _ in range(n_rows):
        q = int(rng.integers(1, 20))
        if rng.random() < 0.01:
            q = int(rng.integers(500, 1000))  # outlier
        quantities.append(q)

    # Order dates (some future)
    base_date = datetime(2024, 1, 1)
    dates = []
    for _ in range(n_rows):
        offset = int(rng.integers(0, 365))
        dt = base_date + timedelta(days=offset)
        if rng.random() < 0.01:
            dt = datetime.utcnow() + timedelta(days=int(rng.integers(30, 365)))
        dates.append(dt.strftime("%Y-%m-%d %H:%M:%S"))

    # Status
    statuses = ["completed", "pending", "shipped", "cancelled", "returned"]
    status_list = [random.choice(statuses) for _ in range(n_rows)]
    # Inject ~1% invalid status
    for i in rng.choice(n_rows, size=max(1, int(n_rows * 0.01)), replace=False):
        status_list[i] = "INVALID_STATUS"

    # Product categories
    categories = ["Electronics", "Clothing", "Books", "Home", "Sports", "Food"]
    category_list = [random.choice(categories) for _ in range(n_rows)]

    df = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": customer_ids,
        "customer_email": emails,
        "order_date": dates,
        "order_total": totals,
        "quantity": quantities,
        "status": status_list,
        "category": category_list,
    })

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

    return df


def generate_reference_customers(
    n_customers: int = 200,
    output_path: Optional[str] = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a reference customer dataset for referential integrity checks.

    Args:
        n_customers: Number of customer records.
        output_path: If provided, saves the DataFrame as CSV.
        seed: Random seed for reproducibility.

    Returns:
        Reference customer DataFrame.
    """
    rng = np.random.default_rng(seed)

    customer_ids = [f"CUST-{i:04d}" for i in range(1, n_customers + 1)]
    names = [f"Customer_{i}" for i in range(1, n_customers + 1)]
    tiers = ["gold", "silver", "bronze", "platinum"]
    tier_list = [tiers[rng.integers(0, len(tiers))] for _ in range(n_customers)]

    df = pd.DataFrame({
        "customer_id": customer_ids,
        "customer_name": names,
        "tier": tier_list,
    })

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

    return df


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent.parent / "sample_data"
    print("Generating synthetic datasets...")
    orders = generate_orders_dataset(
        n_rows=1000,
        output_path=str(base / "orders.csv"),
    )
    print(f"  orders.csv: {len(orders)} rows, {len(orders.columns)} columns")

    customers = generate_reference_customers(
        output_path=str(base / "customers_reference.csv"),
    )
    print(f"  customers_reference.csv: {len(customers)} rows")
    print("Done.")
