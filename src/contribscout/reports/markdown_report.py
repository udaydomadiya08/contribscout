"""Markdown report generator for ContribScout scans."""

from __future__ import annotations

from contribscout.models import ScanReport


def generate_markdown_report(report: ScanReport) -> str:
    """Generate a clean, professional GitHub Flavored Markdown report."""
    lines: list[str] = []

    # Title & Header
    lines.append("# ContribScout — Open-Source Contribution Report")
    lines.append("")
    lines.append(f"**Scan Timestamp**: `{report.timestamp_utc}`  ")
    lines.append(f"**Discovery Backend**: `{report.discovery_backend}`  ")
    lines.append("")

    # Warnings / API notices
    if report.warnings:
        lines.append("> [!WARNING]")
        lines.append("> **Discovery Notices & Constraints:**")
        for w in report.warnings:
            lines.append(f"> - {w}")
        lines.append("")

    # Executive Summary Table
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | Count / Setting |")
    lines.append("| :--- | :--- |")
    lines.append(f"| **Candidates Found** | {report.stats.get('candidates_found', 0)} |")
    lines.append(f"| **Candidates Excluded** | {report.stats.get('candidates_excluded', 0)} |")
    lines.append(f"| **Candidates Scored** | {report.stats.get('candidates_scored', 0)} |")
    langs = report.profile_summary.get("languages", {})
    lang_str = ", ".join(f"{k} ({v})" for k, v in langs.items()) if isinstance(langs, dict) else str(langs)
    lines.append(f"| **Target Languages** | {lang_str or 'Any'} |")
    lines.append(f"| **Experience Level** | {report.profile_summary.get('experience_level', 'intermediate').capitalize()} |")
    lines.append(f"| **Weekly Commitment** | {report.profile_summary.get('hours_per_week', 5.0)} hours/week |")
    lines.append("")

    if not report.opportunities:
        lines.append("> [!NOTE]")
        lines.append("> No contribution opportunities matched all eligibility criteria and minimum score thresholds in this scan.")
        lines.append("> Try broadening your profile's minimum star limit, target languages, or search limits.")
        lines.append("")
        return "\n".join(lines)

    # Top 3 Shortlist with Detailed Investigation Plans
    shortlist = report.opportunities[:3]
    lines.append("## Top Recommendations (Shortlist)")
    lines.append("")

    for scored_opp in shortlist:
        opp = scored_opp.opportunity
        score = scored_opp.score
        badge = f"`[{scored_opp.status_badge}]`" if scored_opp.status_badge else ""
        lines.append(f"### #{scored_opp.rank} — [{opp.repo_full_name}#{opp.number}]({opp.url}): {opp.title} {badge}")
        lines.append("")
        lines.append(
            f"**Score**: `{score.final_score}/10` &nbsp;|&nbsp; "
            f"**Confidence**: `{score.confidence}` ({score.confidence_score*100:.0f}%) &nbsp;|&nbsp; "
            f"**Difficulty**: `{score.estimated_difficulty}` &nbsp;|&nbsp; "
            f"**Estimated Effort**: `{score.estimated_effort_hours}`"
        )
        lines.append("")
        lines.append(f"> **Why this matches**: {score.why_matched}")
        lines.append("")

        # Score Breakdown Table
        lines.append("#### Score Breakdown")
        lines.append("")
        lines.append("| Criterion | Score | Justification |")
        lines.append("| :--- | :---: | :--- |")
        lines.append(f"| Practical Usefulness (25%) | `{score.practical_usefulness}/10` | {score.justifications.get('practical_usefulness', '')} |")
        lines.append(f"| Feasibility (20%) | `{score.feasibility}/10` | {score.justifications.get('feasibility', '')} |")
        lines.append(f"| Technical Depth (20%) | `{score.technical_depth}/10` | {score.justifications.get('technical_depth', '')} |")
        lines.append(f"| Maintainer Responsiveness (15%) | `{score.maintainer_responsiveness}/10` | {score.justifications.get('maintainer_responsiveness', '')} |")
        lines.append(f"| Learning & Portfolio (10%) | `{score.learning_and_portfolio}/10` | {score.justifications.get('learning_and_portfolio', '')} |")
        lines.append(f"| Repository Health (10%) | `{score.repository_health}/10` | {score.justifications.get('repository_health', '')} |")
        lines.append("")

        # 10-Point Investigation Plan
        if score.plan:
            plan = score.plan
            lines.append("#### Actionable Investigation Plan")
            lines.append("")
            lines.append(f"1. **Problem Summary**: {plan.problem_summary}")
            lines.append(f"2. **Why It Matters**: {plan.importance}")
            lines.append(f"3. **What to Read First**: {', '.join(plan.what_to_read_first)}")
            lines.append(f"4. **Likely Files / Subsystems to Inspect**: {', '.join(plan.likely_files_or_subsystems)}")
            lines.append(f"5. **Reproduction Steps**: {', '.join(plan.reproduction_steps)}")
            lines.append(f"6. **Implementation Hypothesis**: {plan.implementation_hypothesis}")
            lines.append(f"7. **Tests & Regression Checks**: {', '.join(plan.test_and_regression_checks)}")
            lines.append(f"8. **Questions for Maintainers**: {', '.join(plan.questions_for_maintainers)}")
            lines.append(f"9. **Potential Risks & Blockers**: {', '.join(plan.risks_and_blockers)}")
            lines.append(f"10. **Suggested First Action**: {plan.suggested_first_action}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Full Ranked Table
    lines.append("## Full Ranked Opportunities")
    lines.append("")
    lines.append("| Rank | Opportunity | Score | Difficulty | Type | Status |")
    lines.append("| :---: | :--- | :---: | :---: | :---: | :---: |")

    for scored_opp in report.opportunities:
        opp = scored_opp.opportunity
        sc = scored_opp.score
        badge = scored_opp.status_badge
        link = f"[{opp.repo_full_name}#{opp.number}]({opp.url})"
        lines.append(f"| {scored_opp.rank} | {link} | `{sc.final_score}/10` | {sc.estimated_difficulty} | {opp.inferred_type} | `{badge}` |")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by [ContribScout](https://github.com/udaydomadiya08/contribscout) — Privacy-conscious open-source discovery agent.*")
    lines.append("")

    return "\n".join(lines)
