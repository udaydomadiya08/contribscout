"""Standalone, responsive dark-mode HTML report generator with strict XSS escaping."""

from __future__ import annotations

import html
from contribscout.models import ScanReport


def generate_html_report(report: ScanReport) -> str:
    """Generate self-contained, beautifully styled HTML report with zero external dependencies."""
    esc = html.escape

    # Prepare executive summary metrics
    stats = report.stats
    langs = report.profile_summary.get("languages", {})
    if isinstance(langs, dict):
        lang_str = ", ".join(f"{k} ({v})" for k, v in langs.items())
    else:
        lang_str = str(langs)

    cards_html: list[str] = []

    for opp in report.opportunities:
        o = opp.opportunity
        sc = opp.score
        plan = sc.plan

        plan_html = ""
        if plan:
            read_items = "".join(f"<li>{esc(item)}</li>" for item in plan.what_to_read_first)
            file_items = "".join(f"<li>{esc(item)}</li>" for item in plan.likely_files_or_subsystems)
            repro_items = "".join(f"<li>{esc(item)}</li>" for item in plan.reproduction_steps)
            test_items = "".join(f"<li>{esc(item)}</li>" for item in plan.test_and_regression_checks)
            question_items = "".join(f"<li>{esc(item)}</li>" for item in plan.questions_for_maintainers)
            risk_items = "".join(f"<li>{esc(item)}</li>" for item in plan.risks_and_blockers)

            plan_html = f"""
            <details class="plan-details">
                <summary>Actionable 10-Point Investigation Plan</summary>
                <div class="plan-body">
                    <p><strong>1. Problem Summary:</strong> {esc(plan.problem_summary)}</p>
                    <p><strong>2. Why It Matters:</strong> {esc(plan.importance)}</p>
                    <p><strong>3. What to Read First:</strong></p>
                    <ul>{read_items}</ul>
                    <p><strong>4. Likely Subsystems / Files:</strong></p>
                    <ul>{file_items}</ul>
                    <p><strong>5. Reproduction Steps:</strong></p>
                    <ul>{repro_items}</ul>
                    <p><strong>6. Implementation Hypothesis:</strong> <em>{esc(plan.implementation_hypothesis)}</em></p>
                    <p><strong>7. Tests & Regressions:</strong></p>
                    <ul>{test_items}</ul>
                    <p><strong>8. Questions for Maintainers:</strong></p>
                    <ul>{question_items}</ul>
                    <p><strong>9. Potential Risks:</strong></p>
                    <ul>{risk_items}</ul>
                    <p><strong>10. Suggested First Action:</strong> <span class="highlight">{esc(plan.suggested_first_action)}</span></p>
                </div>
            </details>
            """

        badge_class = f"badge-{opp.status_badge.lower()}"
        card = f"""
        <article class="opportunity-card">
            <header class="card-header">
                <div class="header-main">
                    <span class="rank-badge">#{opp.rank}</span>
                    <a href="{esc(o.url)}" target="_blank" rel="noopener noreferrer" class="issue-title">
                        {esc(o.repo_full_name)}#{o.number}: {esc(o.title)}
                    </a>
                </div>
                <div class="badges">
                    <span class="badge {badge_class}">{esc(opp.status_badge)}</span>
                    <span class="badge badge-type">{esc(o.inferred_type)}</span>
                    <span class="badge badge-diff">{esc(sc.estimated_difficulty)}</span>
                </div>
            </header>
            <div class="score-banner">
                <div class="score-main">
                    <div class="score-number">{sc.final_score}</div>
                    <div class="score-denom">/ 10</div>
                </div>
                <div class="score-meta">
                    <div><strong>Confidence:</strong> {esc(sc.confidence)} ({sc.confidence_score*100:.0f}%)</div>
                    <div><strong>Estimated Effort:</strong> {esc(sc.estimated_effort_hours)}</div>
                    <div><strong>Why Matched:</strong> {esc(sc.why_matched)}</div>
                </div>
            </div>
            <div class="criteria-grid">
                <div class="criterion-item">
                    <span class="crit-label">Usefulness (25%)</span>
                    <span class="crit-val">{sc.practical_usefulness}/10</span>
                </div>
                <div class="criterion-item">
                    <span class="crit-label">Feasibility (20%)</span>
                    <span class="crit-val">{sc.feasibility}/10</span>
                </div>
                <div class="criterion-item">
                    <span class="crit-label">Tech Depth (20%)</span>
                    <span class="crit-val">{sc.technical_depth}/10</span>
                </div>
                <div class="criterion-item">
                    <span class="crit-label">Maintainer (15%)</span>
                    <span class="crit-val">{sc.maintainer_responsiveness}/10</span>
                </div>
                <div class="criterion-item">
                    <span class="crit-label">Learning (10%)</span>
                    <span class="crit-val">{sc.learning_and_portfolio}/10</span>
                </div>
                <div class="criterion-item">
                    <span class="crit-label">Repo Health (10%)</span>
                    <span class="crit-val">{sc.repository_health}/10</span>
                </div>
            </div>
            {plan_html}
        </article>
        """
        cards_html.append(card)

    warnings_html = ""
    if report.warnings:
        warn_items = "".join(f"<li>{esc(w)}</li>" for w in report.warnings)
        warnings_html = f"""
        <div class="warning-box">
            <h3>Discovery Constraints & Notices</h3>
            <ul>{warn_items}</ul>
        </div>
        """

    cards_joined = "\n".join(cards_html) if cards_html else "<p class='empty-notice'>No opportunities met minimum thresholds.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ContribScout Report — {esc(report.timestamp_utc)}</title>
    <style>
        :root {{
            --bg-base: #0f172a;
            --bg-surface: #1e293b;
            --bg-elevated: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-primary: #38bdf8;
            --accent-green: #34d399;
            --accent-amber: #fbbf24;
            --accent-rose: #f43f5e;
            --border: #334155;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: var(--font-family);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1040px;
            margin: 0 auto;
        }}
        header.app-header {{
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }}
        h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--accent-primary);
            letter-spacing: -0.02em;
        }}
        .header-meta {{
            color: var(--text-secondary);
            font-size: 0.95rem;
            margin-top: 0.5rem;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.2rem;
        }}
        .stat-num {{
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent-primary);
        }}
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .warning-box {{
            background: rgba(251, 191, 36, 0.1);
            border: 1px solid var(--accent-amber);
            border-radius: 8px;
            padding: 1.2rem;
            margin-bottom: 2rem;
            color: #fef3c7;
        }}
        .warning-box h3 {{
            color: var(--accent-amber);
            margin-bottom: 0.5rem;
            font-size: 1.05rem;
        }}
        .warning-box ul {{
            padding-left: 1.5rem;
        }}
        .opportunity-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.8rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}
        .opportunity-card:hover {{
            border-color: var(--accent-primary);
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 0.8rem;
            margin-bottom: 1rem;
        }}
        .header-main {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex: 1;
        }}
        .rank-badge {{
            background: var(--bg-elevated);
            color: var(--text-primary);
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 6px;
            font-size: 0.9rem;
        }}
        .issue-title {{
            color: var(--text-primary);
            font-size: 1.2rem;
            font-weight: 600;
            text-decoration: none;
        }}
        .issue-title:hover {{
            color: var(--accent-primary);
            text-decoration: underline;
        }}
        .badges {{
            display: flex;
            gap: 0.5rem;
        }}
        .badge {{
            padding: 0.25rem 0.6rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-new {{ background: rgba(52, 211, 153, 0.15); color: var(--accent-green); border: 1px solid var(--accent-green); }}
        .badge-updated {{ background: rgba(251, 191, 36, 0.15); color: var(--accent-amber); border: 1px solid var(--accent-amber); }}
        .badge-seen {{ background: var(--bg-elevated); color: var(--text-muted); }}
        .badge-type {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-primary); }}
        .badge-diff {{ background: var(--bg-elevated); color: var(--text-secondary); }}
        .score-banner {{
            display: flex;
            background: var(--bg-base);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            gap: 1.5rem;
            align-items: center;
        }}
        .score-main {{
            display: flex;
            align-items: baseline;
            gap: 0.2rem;
        }}
        .score-number {{
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--accent-green);
        }}
        .score-denom {{
            color: var(--text-muted);
            font-size: 1.1rem;
        }}
        .score-meta {{
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        .criteria-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}
        .criterion-item {{
            background: var(--bg-base);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            font-size: 0.82rem;
        }}
        .crit-label {{ color: var(--text-muted); }}
        .crit-val {{ font-weight: 700; color: var(--text-primary); }}
        .plan-details {{
            margin-top: 1rem;
            border-top: 1px solid var(--border);
            padding-top: 0.8rem;
        }}
        .plan-details summary {{
            cursor: pointer;
            color: var(--accent-primary);
            font-weight: 600;
            user-select: none;
        }}
        .plan-body {{
            background: var(--bg-base);
            border-radius: 8px;
            padding: 1rem;
            margin-top: 0.8rem;
            font-size: 0.9rem;
        }}
        .plan-body p {{ margin-bottom: 0.6rem; }}
        .plan-body ul {{ padding-left: 1.5rem; margin-bottom: 0.6rem; }}
        .highlight {{ color: var(--accent-green); font-weight: 600; }}
        footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 3rem;
            border-top: 1px solid var(--border);
            padding-top: 1.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="app-header">
            <h1>ContribScout</h1>
            <p class="header-meta">
                Scan UTC: <strong>{esc(report.timestamp_utc)}</strong> &nbsp;|&nbsp;
                Backend: <strong>{esc(report.discovery_backend)}</strong> &nbsp;|&nbsp;
                Languages: <strong>{esc(lang_str)}</strong>
            </p>
        </header>

        <section class="summary-stats">
            <div class="stat-card">
                <div class="stat-num">{stats.get('candidates_found', 0)}</div>
                <div class="stat-label">Candidates Discovered</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{stats.get('candidates_excluded', 0)}</div>
                <div class="stat-label">Ineligible / Excluded</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">{stats.get('candidates_scored', 0)}</div>
                <div class="stat-label">Opportunities Scored</div>
            </div>
        </section>

        {warnings_html}

        <section class="opportunities-list">
            <h2 style="margin-bottom: 1.2rem; font-size: 1.4rem;">Ranked Recommendations</h2>
            {cards_joined}
        </section>

        <footer>
            Generated by <strong>ContribScout</strong> — Local-first open source opportunity scout.
        </footer>
    </div>
</body>
</html>
"""
