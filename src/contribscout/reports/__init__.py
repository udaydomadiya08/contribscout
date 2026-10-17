"""Reporting subsystem for ContribScout."""

from contribscout.reports.html_report import generate_html_report
from contribscout.reports.json_report import generate_json_report
from contribscout.reports.markdown_report import generate_markdown_report

__all__ = [
    "generate_markdown_report",
    "generate_json_report",
    "generate_html_report",
]
