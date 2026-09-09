# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
Trend tracking: persists validation run results to SQLite for
historical analysis and quality trend visualization.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from sentinel.models import ValidationReport


DEFAULT_DB_PATH = "sentinel_history.db"


class TrendStore:
    """SQLite-backed store for validation run history."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        """Initialize the trend store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS validation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    suite_name TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    total_checks INTEGER NOT NULL,
                    passed_checks INTEGER NOT NULL,
                    failed_checks INTEGER NOT NULL,
                    warning_checks INTEGER NOT NULL,
                    critical_failures INTEGER NOT NULL,
                    overall_score REAL NOT NULL,
                    execution_time_ms REAL NOT NULL,
                    check_results_json TEXT,
                    anomaly_results_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_suite_timestamp
                ON validation_runs (suite_name, timestamp)
            """)
            conn.commit()
        finally:
            conn.close()

    def save_run(self, report: ValidationReport) -> int:
        """Save a validation report to the trend database.

        Args:
            report: The validation report to persist.

        Returns:
            The row ID of the inserted record.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            check_results_json = json.dumps(
                [r.model_dump() for r in report.check_results],
                default=str,
            )
            anomaly_results_json = json.dumps(
                [r.model_dump() for r in report.anomaly_results],
                default=str,
            )

            cursor = conn.execute(
                """
                INSERT INTO validation_runs
                (run_id, suite_name, data_source, timestamp, total_checks,
                 passed_checks, failed_checks, warning_checks, critical_failures,
                 overall_score, execution_time_ms, check_results_json, anomaly_results_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.run_id,
                    report.suite_name,
                    report.data_source,
                    report.timestamp.isoformat(),
                    report.total_checks,
                    report.passed_checks,
                    report.failed_checks,
                    report.warning_checks,
                    report.critical_failures,
                    report.overall_score,
                    report.execution_time_ms,
                    check_results_json,
                    anomaly_results_json,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def get_history(
        self,
        suite_name: str,
        limit: int = 30,
    ) -> list[dict]:
        """Retrieve historical validation runs for a suite.

        Args:
            suite_name: Name of the expectation suite.
            limit: Maximum number of runs to return.

        Returns:
            List of run summary dictionaries, most recent first.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT run_id, suite_name, data_source, timestamp,
                       total_checks, passed_checks, failed_checks,
                       warning_checks, critical_failures, overall_score,
                       execution_time_ms
                FROM validation_runs
                WHERE suite_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (suite_name, limit),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_run_detail(self, run_id: str) -> Optional[dict]:
        """Retrieve full details of a specific validation run.

        Args:
            run_id: The unique run identifier.

        Returns:
            Full run dictionary including check/anomaly results, or None.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM validation_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["check_results"] = json.loads(result.pop("check_results_json", "[]"))
            result["anomaly_results"] = json.loads(result.pop("anomaly_results_json", "[]"))
            return result
        finally:
            conn.close()

    def get_score_trend(self, suite_name: str, limit: int = 30) -> list[dict]:
        """Get quality score trend data for charting.

        Args:
            suite_name: Name of the expectation suite.
            limit: Maximum data points to return.

        Returns:
            List of {timestamp, overall_score, passed_checks, failed_checks}.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT timestamp, overall_score, passed_checks, failed_checks,
                       critical_failures
                FROM validation_runs
                WHERE suite_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (suite_name, limit),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]
        finally:
            conn.close()

    def delete_old_runs(self, suite_name: str, keep_latest: int = 100) -> int:
        """Delete old runs, keeping only the most recent ones.

        Args:
            suite_name: Name of the expectation suite.
            keep_latest: Number of most recent runs to retain.

        Returns:
            Number of deleted rows.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                DELETE FROM validation_runs
                WHERE suite_name = ? AND id NOT IN (
                    SELECT id FROM validation_runs
                    WHERE suite_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
                """,
                (suite_name, suite_name, keep_latest),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
