"""Difficulty estimation and structured 10-point contribution investigation planning."""

from __future__ import annotations

import re
from typing import List, Tuple

from contribscout.models import InvestigationPlan, Opportunity, UserProfile


def extract_mentioned_filepaths(text: str) -> List[str]:
    """
    Extract source code filepaths or module paths explicitly mentioned in issue text.
    Strictly avoids inventing non-existent files.
    """
    # Strip URLs first to avoid matching parts of web links
    cleaned_text = re.sub(r"https?://[^\s)\]]+", "", text)
    cleaned_text = re.sub(r"//[^\s)\]]+", "", cleaned_text)

    patterns = [
        r"`([a-zA-Z0-9_\-\./\\]+\.(?:py|js|ts|jsx|tsx|rs|go|c|cpp|h|java|rb|sh|yaml|yml|toml|json))`",
        r"(?:^|[\s(\"'])([a-zA-Z0-9_\-\./\\]+\.(?:py|js|ts|jsx|tsx|rs|go|c|cpp|h|java|rb|sh|yaml|yml|toml|json))(?:[\s)\"',:]|$)",
    ]
    found = set()
    for pat in patterns:
        for match in re.findall(pat, cleaned_text):
            clean = match.strip("`'\"()[],:;").strip()
            if clean and not clean.startswith(("//", "http", "www")):
                if len(clean) < 80 and not any(ext in clean.lower() for ext in [".com", ".org", ".io", ".png", ".jpg", ".jpeg", ".gif"]):
                    found.add(clean)
    return sorted(list(found))[:5]


def estimate_difficulty(
    opportunity: Opportunity,
    profile: UserProfile,
) -> Tuple[str, str, List[str]]:
    """
    Estimate difficulty category, effort range, and difficulty reasoning factors.
    Returns: (category, effort_hours_str, reasoning_factors)
    """
    labels_lower = [lbl.lower() for lbl in opportunity.labels]
    title_lower = opportunity.title.lower()
    body_lower = opportunity.body.lower()
    factors: List[str] = []

    # Difficulty score accumulator (0 to 10)
    # 0-3: Beginner, 4-6: Intermediate, 7-8: Advanced, 9-10: Expert
    diff_score = 5.0

    # 1. Good first issue signals
    if any("good first issue" in lbl or "good-first-issue" in lbl or "easy" in lbl for lbl in labels_lower):
        diff_score -= 2.5
        factors.append("Tagged with beginner-friendly label.")

    # 2. Documentation or typo signals
    if opportunity.inferred_type == "documentation" or "typo" in title_lower or "docs" in labels_lower:
        diff_score -= 2.0
        factors.append("Documentation / textual modification task.")

    # 3. Architectural / Breaking / Refactoring signals
    if any(k in title_lower or k in labels_lower for k in ["breaking", "refactor", "redesign", "architecture"]):
        diff_score += 2.0
        factors.append("Involves architectural changes or refactoring.")

    # 4. Performance / Memory / Concurrency signals
    if any(k in title_lower or k in labels_lower for k in ["memory leak", "deadlock", "race condition", "concurrency", "perf", "performance"]):
        diff_score += 1.5
        factors.append("Requires performance profiling or concurrency analysis.")

    # 5. Stack trace presence indicates well-isolated error
    if "traceback" in body_lower or "stack trace" in body_lower or "error:" in body_lower:
        diff_score -= 0.5
        factors.append("Contains error stack trace aiding reproduction.")

    # 6. Issue length and complexity
    if len(opportunity.body) > 1500:
        factors.append("Detailed specification with extensive context.")
    elif len(opportunity.body) < 150:
        diff_score += 1.0
        factors.append("Sparse description requiring maintainer disambiguation.")

    # Map score to category and effort range
    if diff_score <= 3.5:
        category = "Beginner"
        effort = "1-3 hours (Estimated)"
    elif diff_score <= 6.5:
        category = "Intermediate"
        effort = "4-8 hours (Estimated)"
    elif diff_score <= 8.5:
        category = "Advanced"
        effort = "1-3 days (Estimated)"
    else:
        category = "Expert"
        effort = "3-5+ days (Estimated)"

    return category, effort, factors


def generate_investigation_plan(
    opportunity: Opportunity,
    profile: UserProfile,
    difficulty_category: str,
) -> InvestigationPlan:
    """
    Generate an actionable 10-point contribution investigation plan.
    Strictly relies on observable issue evidence without fabricating files or maintainer claims.
    """
    body_snippet = opportunity.body.strip()
    if len(body_snippet) > 160:
        body_snippet = body_snippet[:157] + "..."

    problem_summary = (
        f"Issue #{opportunity.number}: {opportunity.title}. "
        f"{body_snippet if body_snippet else 'No detailed body provided in issue description.'}"
    )

    importance = (
        f"Resolves a {opportunity.inferred_type} in {opportunity.repo_full_name}. "
        f"Helps improve repository stability and addresses reported community friction."
    )

    # 3. What to read first
    what_to_read = [
        f"Issue discussion thread: {opportunity.url}",
        f"Repository README and guidelines: https://github.com/{opportunity.repo_full_name}#readme",
    ]
    if opportunity.repository and opportunity.repository.primary_language:
        what_to_read.append(f"Contributing documentation for {opportunity.repository.primary_language} components.")

    # 4. Likely files or subsystems (strictly evidence-based)
    mentioned_files = extract_mentioned_filepaths(opportunity.body + " " + opportunity.title)
    if mentioned_files:
        likely_files = [f"Directly referenced in issue: `{f}`" for f in mentioned_files]
    else:
        primary_lang = opportunity.repository.primary_language if opportunity.repository else "source"
        title_words = opportunity.title.split()
        keyword = title_words[0] if title_words else "core"
        likely_files = [
            f"No specific files mentioned in issue description. Inspect top-level `{primary_lang}` modules "
            f"and test suites matching '{keyword}'."
        ]

    # 5. Reproduction steps
    reproduction_steps = []
    if "reproduce" in opportunity.body.lower() or "steps to reproduce" in opportunity.body.lower():
        reproduction_steps.append("Follow the step-by-step reproduction code snippet provided in the issue description.")
    else:
        reproduction_steps.append("Construct a minimal reproducing test case or script matching the reported error condition.")
    reproduction_steps.append("Verify the failure triggers cleanly on the latest default branch commit.")

    # 6. Implementation hypothesis
    hypothesis = (
        f"[Hypothesis]: For this {opportunity.inferred_type}, identify where input validation, logic flow, "
        f"or state handling fails under the specified edge cases, and apply a scoped patch without side effects."
    )

    # 7. Tests and regression checks
    test_checks = [
        "Write a targeted regression test reproducing the issue before applying the fix.",
        "Run the existing local test suite (e.g., pytest, make test) to verify no regressions.",
        "Check code style and linter compliance according to project CI configuration.",
    ]

    # 8. Questions for maintainers
    maintainer_questions = [
        "Is this issue currently open for external contribution?",
        "Is there a preferred architectural approach or deprecation policy we should follow for this change?",
    ]
    if not opportunity.body or len(opportunity.body) < 100:
        maintainer_questions.append("Could maintainers provide additional environment details or logs to clarify reproduction?")

    # 9. Risks and blockers
    risks = []
    if opportunity.comments_count > 10:
        risks.append("Extensive discussion thread; review prior comments to avoid duplicating abandoned attempts.")
    if opportunity.assignees:
        risks.append(f"Issue has assignees ({', '.join(opportunity.assignees)}); confirm availability before starting.")
    if not opportunity.repository or not opportunity.repository.license:
        risks.append("Repository license is unverified; verify contribution terms.")
    if not risks:
        risks.append("Ensure patch preserves backward compatibility and does not break public APIs.")

    # 10. Suggested first action
    first_action = (
        f"Review the issue conversation at {opportunity.url}. If unassigned, leave a brief, polite comment "
        f"stating your intent to investigate and link any preliminary findings."
    )

    return InvestigationPlan(
        problem_summary=problem_summary,
        importance=importance,
        what_to_read_first=what_to_read,
        likely_files_or_subsystems=likely_files,
        reproduction_steps=reproduction_steps,
        implementation_hypothesis=hypothesis,
        test_and_regression_checks=test_checks,
        questions_for_maintainers=maintainer_questions,
        risks_and_blockers=risks,
        suggested_first_action=first_action,
    )
