"""Unit tests for report generation across Markdown, JSON, and HTML formats."""

import json
from pathlib import Path
import pytest

from contribscout.analysis.difficulty import generate_investigation_plan
from contribscout.models import (
    Opportunity,
    OpportunityScore,
    Repository,
    ScanReport,
    ScoredOpportunity,
)
from contribscout.reports.html_report import generate_html_report
from contribscout.reports.json_report import generate_json_report
from contribscout.reports.markdown_report import generate_markdown_report


@pytest.fixture
def sample_report():
    repo = Repository(
        owner="acme",
        name="fast-nlp",
        full_name="acme/fast-nlp",
        stars=1000,
        license="MIT",
        primary_language="python",
    )
    opp = Opportunity(
        id="acme/fast-nlp#42",
        repo_full_name="acme/fast-nlp",
        number=42,
        title="Fix tokenizer crash <script>alert('xss')</script>",
        body="Detailed body with tokenizer.py error.",
        url="https://github.com/acme/fast-nlp/issues/42",
        repository=repo,
        inferred_type="bug",
    )
    score = OpportunityScore(
        opportunity_id=opp.id,
        final_score=8.5,
        practical_usefulness=8.0,
        feasibility=8.5,
        technical_depth=8.0,
        maintainer_responsiveness=8.0,
        learning_and_portfolio=8.5,
        repository_health=9.0,
        score_breakdown={"practical_usefulness": 8.0, "feasibility": 8.5},
        justifications={"practical_usefulness": "Addresses core tokenizer error"},
        confidence="High",
        confidence_score=0.9,
        estimated_difficulty="Intermediate",
        estimated_effort_hours="4-8 hours",
        why_matched="Matches Python proficiency",
        plan=generate_investigation_plan(opp, None, "Intermediate"),
    )
    scored_opp = ScoredOpportunity(opportunity=opp, score=score, rank=1, status_badge="NEW")

    return ScanReport(
        timestamp_utc="2026-10-17 12:00:00 UTC",
        profile_summary={"languages": {"python": "advanced"}, "experience_level": "intermediate"},
        search_scope={"languages": ["python"]},
        stats={"candidates_found": 10, "candidates_excluded": 8, "candidates_scored": 1},
        opportunities=[scored_opp],
        warnings=["Search rate limit notice"],
        discovery_backend="github_api",
    )


def test_markdown_report(sample_report):
    md = generate_markdown_report(sample_report)
    assert "# ContribScout — Open-Source Contribution Report" in md
    assert "acme/fast-nlp#42" in md
    assert "8.5/10" in md
    assert "Actionable Investigation Plan" in md
    assert "Search rate limit notice" in md
    # Secrets should not be present
    assert "token" not in md.lower() or "tokenizer" in md.lower()


def test_json_report(sample_report):
    json_str = generate_json_report(sample_report)
    parsed = json.loads(json_str)

    assert parsed["timestamp_utc"] == "2026-10-17 12:00:00 UTC"
    assert len(parsed["opportunities"]) == 1
    assert parsed["opportunities"][0]["score"]["final_score"] == 8.5
    assert parsed["opportunities"][0]["rank"] == 1


def test_html_report_xss_prevention(sample_report):
    html_str = generate_html_report(sample_report)
    assert "<!DOCTYPE html>" in html_str
    assert "acme/fast-nlp" in html_str
    # Crucial security check: raw script tag must be properly escaped
    assert "<script>alert('xss')</script>" not in html_str
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html_str
