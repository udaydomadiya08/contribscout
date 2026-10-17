"""Repository health and contribution readiness assessment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from contribscout.models import Repository

POPULAR_OSI_LICENSES = {
    "mit",
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "gpl-3.0",
    "lgpl-3.0",
    "mpl-2.0",
    "isc",
    "unlicense",
}


def parse_iso_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def calculate_repository_health(repo: Optional[Repository]) -> Tuple[float, List[str], List[str]]:
    """
    Calculate an explainable repository health score (0.0 to 10.0)
    along with evidence strings and negative signals.
    """
    if not repo:
        return 5.0, ["Repository metadata is unavailable (default neutral health assumed)."], ["Missing repository metadata."]

    if repo.is_archived:
        return 0.0, ["Repository is archived."], ["Repository is archived and read-only."]

    score = 5.0
    evidence: List[str] = []
    negatives: List[str] = []

    # 1. Activity / pushed_at recency
    if repo.pushed_at:
        pushed_dt = parse_iso_date(repo.pushed_at)
        if pushed_dt:
            days_since_push = (datetime.now(timezone.utc) - pushed_dt).days
            if days_since_push <= 7:
                score += 2.5
                evidence.append(f"Highly active repository (pushed {days_since_push} days ago).")
            elif days_since_push <= 30:
                score += 2.0
                evidence.append(f"Recently active repository (pushed {days_since_push} days ago).")
            elif days_since_push <= 90:
                score += 1.0
                evidence.append(f"Active repository (pushed {days_since_push} days ago).")
            elif days_since_push <= 180:
                score -= 0.5
                negatives.append(f"Moderate activity lapse ({days_since_push} days since last push).")
            else:
                score -= 2.0
                negatives.append(f"Infrequent activity ({days_since_push} days since last push).")
    else:
        negatives.append("Push activity date unknown.")

    # 2. Stars and community engagement
    if repo.stars >= 500:
        score += 1.5
        evidence.append(f"Strong community adoption ({repo.stars:,} stars, {repo.forks:,} forks).")
    elif repo.stars >= 100:
        score += 1.0
        evidence.append(f"Established community ({repo.stars} stars, {repo.forks} forks).")
    elif repo.stars >= 20:
        score += 0.5
        evidence.append(f"Growing repository ({repo.stars} stars).")
    else:
        negatives.append(f"Low star count ({repo.stars} stars); maintainer review capacity may be unverified.")

    # 3. License verification
    if repo.license:
        lic_lower = repo.license.lower()
        if any(osi in lic_lower for osi in POPULAR_OSI_LICENSES):
            score += 1.0
            evidence.append(f"Open-source OSI compliant license verified ({repo.license}).")
        else:
            evidence.append(f"Repository license: {repo.license}.")
    else:
        negatives.append("No explicit license detected in repository metadata.")
        score -= 0.5

    # 4. Fork penalty if it's a secondary fork
    if repo.is_fork:
        score -= 1.0
        negatives.append("Repository is a fork of another project.")

    clamped_score = max(0.0, min(10.0, round(score, 1)))
    repo.health_score = clamped_score
    return clamped_score, evidence, negatives
