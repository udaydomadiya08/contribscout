"""JSON report generator for ContribScout scans."""

from __future__ import annotations

import json
from contribscout.models import ScanReport


def generate_json_report(report: ScanReport, indent: int = 2) -> str:
    """Generate structured JSON string from ScanReport model."""
    return json.dumps(report.to_dict(), indent=indent)
