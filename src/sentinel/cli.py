# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
CLI interface for running validations, viewing history, and generating reports.
Uses Click for argument parsing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from sentinel.engine import run_validation
from sentinel.expectations import load_expectations, validate_expectations
from sentinel.report import generate_console_report, generate_html_report
from sentinel.trend import TrendStore


@click.group()
@click.version_option(version="1.0.0", prog_name="sentinel")
def cli() -> None:
    """Data Quality Sentinel - Automated Data Validation Framework."""
    pass


@cli.command()
@click.argument("expectations_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=None, help="HTML report output path")
@click.option("--db", default="sentinel_history.db", help="SQLite history database path")
@click.option("--no-anomaly", is_flag=True, help="Skip anomaly detection")
@click.option("--no-trend", is_flag=True, help="Skip saving to trend database")
@click.option("--quiet", "-q", is_flag=True, help="Only output exit code, no console report")
def validate(
    expectations_file: str,
    output: str | None,
    db: str,
    no_anomaly: bool,
    no_trend: bool,
    quiet: bool,
) -> None:
    """Run validation checks against an expectations file.

    EXPECTATIONS_FILE is the path to a YAML expectations file.

    Exit codes: 0 = all checks passed, 1 = critical failures, 2 = warnings only.
    """
    try:
        suite = load_expectations(expectations_file)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error loading expectations: {e}", err=True)
        sys.exit(3)

    # Validate the suite configuration
    errors = validate_expectations(suite)
    if errors:
        click.echo("Expectation validation errors:", err=True)
        for err in errors:
            click.echo(f"  - {err}", err=True)
        sys.exit(3)

    # Run validation
    report = run_validation(
        suite,
        run_anomaly_detection=not no_anomaly,
    )

    # Save to trend database
    trend_data: list[dict] = []
    if not no_trend:
        store = TrendStore(db)
        store.save_run(report)
        trend_data = store.get_score_trend(suite.suite_name)

    # Generate HTML report
    if output:
        html_path = generate_html_report(
            report,
            output_path=output,
            trend_data=trend_data,
        )
        if not quiet:
            click.echo(f"HTML report saved to: {html_path}")

    # Console output
    if not quiet:
        click.echo(generate_console_report(report))

    # Exit code based on results
    if report.critical_failures > 0:
        sys.exit(1)
    elif report.failed_checks > 0:
        sys.exit(2)
    else:
        sys.exit(0)


@cli.command()
@click.argument("suite_name")
@click.option("--db", default="sentinel_history.db", help="SQLite history database path")
@click.option("--limit", "-n", default=20, help="Number of runs to show")
def history(suite_name: str, db: str, limit: int) -> None:
    """View validation run history for a suite.

    SUITE_NAME is the name of the expectation suite to query.
    """
    store = TrendStore(db)
    runs = store.get_history(suite_name, limit=limit)

    if not runs:
        click.echo(f"No history found for suite '{suite_name}'")
        return

    click.echo(f"\nValidation History: {suite_name} (last {len(runs)} runs)")
    click.echo("-" * 80)
    click.echo(f"{'Run ID':<10} {'Timestamp':<22} {'Score':>7} {'Passed':>8} {'Failed':>8} {'Critical':>10}")
    click.echo("-" * 80)

    for run in runs:
        click.echo(
            f"{run['run_id']:<10} "
            f"{run['timestamp'][:19]:<22} "
            f"{run['overall_score']:>6.1f}% "
            f"{run['passed_checks']:>8} "
            f"{run['failed_checks']:>8} "
            f"{run['critical_failures']:>10}"
        )


@cli.command()
@click.argument("expectations_file", type=click.Path(exists=True))
def check(expectations_file: str) -> None:
    """Validate an expectations YAML file without running checks.

    EXPECTATIONS_FILE is the path to the YAML expectations file.
    """
    try:
        suite = load_expectations(expectations_file)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error loading expectations: {e}", err=True)
        sys.exit(1)

    errors = validate_expectations(suite)
    if errors:
        click.echo("Validation errors found:")
        for err in errors:
            click.echo(f"  - {err}")
        sys.exit(1)
    else:
        click.echo(f"Expectations file is valid: {suite.suite_name}")
        click.echo(f"  Data source: {suite.data_source.name} ({suite.data_source.path})")
        click.echo(f"  Checks defined: {len(suite.checks)}")
        sys.exit(0)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
