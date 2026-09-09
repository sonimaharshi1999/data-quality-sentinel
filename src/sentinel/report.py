# Data Quality Sentinel - Automated Data Validation Framework
# Author: Maharshi Soni | License: MIT
"""
HTML report generator using Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from sentinel.models import ValidationReport


# Default template directory (sibling of the package source)
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def generate_html_report(
    report: ValidationReport,
    output_path: str = "quality_report.html",
    template_dir: Optional[str] = None,
    trend_data: Optional[list[dict]] = None,
) -> str:
    """Render a ValidationReport to an HTML file.

    Args:
        report: The validation report to render.
        output_path: Destination file path for the HTML report.
        template_dir: Directory containing the Jinja2 template.
            Defaults to the project's templates/ directory.
        trend_data: Optional historical trend data for the chart.

    Returns:
        The absolute path to the generated HTML file.
    """
    tpl_dir = Path(template_dir) if template_dir else _TEMPLATE_DIR
    if not tpl_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {tpl_dir}")

    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=True,
    )
    template = env.get_template("report.html")

    html = template.render(
        report=report,
        trend_data=trend_data or [],
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    return str(out.resolve())


def generate_console_report(report: ValidationReport) -> str:
    """Generate a text summary of the validation report for CLI output.

    Args:
        report: The validation report to summarize.

    Returns:
        Formatted text report.
    """
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"  DATA QUALITY REPORT: {report.suite_name}")
    lines.append("=" * 70)
    lines.append(f"  Run ID:     {report.run_id}")
    lines.append(f"  Source:     {report.data_source}")
    lines.append(f"  Timestamp:  {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"  Duration:   {report.execution_time_ms:.1f}ms")
    lines.append("-" * 70)

    status = "PASSED" if report.passed else "FAILED"
    lines.append(f"  Status: {status}  |  Score: {report.overall_score:.1f}%")
    lines.append(
        f"  Checks: {report.total_checks} total, "
        f"{report.passed_checks} passed, "
        f"{report.failed_checks} failed "
        f"({report.critical_failures} critical)"
    )
    lines.append("-" * 70)

    # Check results
    for r in report.check_results:
        icon = "[PASS]" if r.passed else "[FAIL]"
        sev = f"[{r.severity.value.upper()}]" if not r.passed else ""
        lines.append(f"  {icon} {sev} {r.check_name}: {r.message}")

    # Anomaly results
    if report.anomaly_results:
        lines.append("-" * 70)
        lines.append("  ANOMALY DETECTION:")
        for a in report.anomaly_results:
            icon = "[!]" if a.is_anomaly else "[ok]"
            lines.append(f"  {icon} {a.message}")

    lines.append("=" * 70)
    return "\n".join(lines)
