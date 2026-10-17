"""Eligibility evaluation and diagnostic filtering for open-source opportunities."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import List, Optional

from contribscout.models import EligibilityResult, Opportunity, UserProfile

# Known non-OSI or non-free license markers
KNOWN_PROPRIETARY_LICENSES = {"no-license", "commercial", "all-rights-reserved"}


def parse_iso_date(date_str: str) -> Optional[datetime]:
    """Parse ISO 8601 timestamp string into UTC datetime."""
    if not date_str:
        return None
    try:
        # Handle trailing Z or offsets
        cleaned = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except Exception:
        return None


def evaluate_eligibility(
    opportunity: Opportunity,
    profile: UserProfile,
) -> EligibilityResult:
    """
    Evaluate whether an opportunity is eligible for recommendation.
    Returns EligibilityResult with boolean verdict, reasons, warnings, and penalties.
    """
    reasons: List[str] = []
    warnings: List[str] = []
    penalties: dict[str, float] = {}

    repo = opportunity.repository

    # 1. State check
    if opportunity.state != "open":
        reasons.append(f"Issue is closed (state: {opportunity.state}).")

    # 2. Repository archive check
    if repo and repo.is_archived:
        reasons.append("Repository is archived and read-only.")

    # 3. Active assignee check
    if opportunity.assignees:
        assignee_list = ", ".join(opportunity.assignees)
        reasons.append(f"Issue is already assigned to {assignee_list}.")

    # 4. Solved pull request check
    if opportunity.has_pull_request:
        reasons.append("Issue has an associated pull request indicating ongoing or completed work.")

    # 5. Locked check
    if opportunity.is_locked:
        reasons.append("Issue conversation is locked by repository maintainers.")

    # 6. Excluded repos and orgs
    if repo:
        if repo.full_name.lower() in [r.lower() for r in profile.exclude_repos]:
            reasons.append(f"Repository {repo.full_name} is explicitly excluded in user profile.")

        if repo.owner.lower() in [o.lower() for o in profile.exclude_orgs]:
            reasons.append(f"Organization {repo.owner} is explicitly excluded in user profile.")

        # Excluded topics
        for topic in repo.topics:
            if topic.lower() in [t.lower() for t in profile.exclude_topics]:
                reasons.append(f"Repository topic '{topic}' is excluded in user profile.")
                break

    # 7. Excluded labels
    for lbl in opportunity.labels:
        if lbl.lower() in [el.lower() for el in profile.exclude_labels]:
            reasons.append(f"Issue has excluded label '{lbl}'.")
            break

    # 8. Spam or vague description check
    body = opportunity.body.strip()
    if len(body) < 25:
        # Check if title has enough substance, otherwise flag
        if len(opportunity.title.strip()) < 15:
            reasons.append("Issue description and title are too brief or vague (< 25 chars) to be actionable.")
        else:
            warnings.append("Issue body is sparse or empty; investigation details may be limited.")
            penalties["sparse_body"] = 1.5

    # Check for obvious automated bot spam or dependabot bumps that aren't developer contribution targets
    bot_markers = ["[dependabot]", "[renovate]", "automated bump", "bump version to"]
    if any(marker in opportunity.title.lower() for marker in bot_markers):
        reasons.append("Issue appears to be an automated dependency bump or bot notification.")

    # 9. Repository activity freshness
    if repo and repo.pushed_at:
        pushed_dt = parse_iso_date(repo.pushed_at)
        if pushed_dt:
            now = datetime.now(timezone.utc)
            days_inactive = (now - pushed_dt).days
            if days_inactive > profile.min_recent_activity_days:
                reasons.append(
                    f"Repository inactive for {days_inactive} days "
                    f"(exceeds user threshold of {profile.min_recent_activity_days} days)."
                )

    # 10. Star requirements
    if repo:
        if profile.min_stars and repo.stars < profile.min_stars:
            reasons.append(f"Repository stars ({repo.stars}) below configured minimum ({profile.min_stars}).")
        if profile.max_stars and repo.stars > profile.max_stars:
            reasons.append(f"Repository stars ({repo.stars}) exceeds configured maximum ({profile.max_stars}).")

    # 11. Stale issue penalty (not outright exclusion, as well-defined long-standing bugs can be valuable)
    if opportunity.created_at:
        created_dt = parse_iso_date(opportunity.created_at)
        if created_dt:
            age_days = (datetime.now(timezone.utc) - created_dt).days
            if age_days > 365 and opportunity.comments_count == 0:
                penalties["stale_no_comments"] = 2.0
                warnings.append(f"Issue was opened {age_days} days ago without comments.")

    is_eligible = len(reasons) == 0
    return EligibilityResult(
        is_eligible=is_eligible,
        reasons=reasons,
        warnings=warnings,
        penalties=penalties,
    )
