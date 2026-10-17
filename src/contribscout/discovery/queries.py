"""Search query generation heuristics for ContribScout discovery."""

from __future__ import annotations

from typing import List
from contribscout.models import UserProfile


def build_search_queries(profile: UserProfile, max_queries: int = 6) -> List[str]:
    """
    Construct a prioritized, diversified list of GitHub search query strings
    tailored to the user's profile.
    """
    queries: List[str] = []

    # 1. Priority repositories if specified
    if profile.priority_repos:
        for repo in profile.priority_repos[:3]:
            queries.append(f"repo:{repo} is:issue is:open")

    # 2. Priority orgs if specified
    if profile.priority_orgs:
        for org in profile.priority_orgs[:2]:
            queries.append(f"org:{org} is:issue is:open")

    # Pick top primary language
    primary_lang = "python"
    if profile.languages:
        # Pick language with highest proficiency
        lang_rank = {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}
        sorted_langs = sorted(
            profile.languages.items(),
            key=lambda item: lang_rank.get(item[1].lower(), 1),
            reverse=True,
        )
        primary_lang = sorted_langs[0][0]

    min_stars = profile.min_stars or 20

    # 3. "Good first issue" & beginner queries if appropriate
    if (
        "good-first-issue" in profile.contribution_types
        or profile.experience_level in ("beginner", "intermediate")
        or profile.desired_difficulty in ("beginner", "intermediate")
    ):
        queries.append(
            f'is:issue is:open label:"good first issue","good-first-issue","help wanted" '
            f'language:{primary_lang} stars:>={min_stars} sort:updated-desc'
        )

    # 4. Bugs and fixes
    if "bug" in profile.contribution_types:
        queries.append(
            f'is:issue is:open label:"bug","fix" language:{primary_lang} '
            f'stars:>={min_stars} sort:updated-desc'
        )

    # 5. Domain interest queries
    if profile.interests:
        for interest in profile.interests[:2]:
            clean_interest = interest.replace(" ", "-").lower()
            queries.append(
                f'is:issue is:open topic:{clean_interest} language:{primary_lang} '
                f'stars:>={min_stars} sort:updated-desc'
            )

    # 6. Framework-specific queries
    if profile.frameworks:
        for fw in profile.frameworks[:2]:
            clean_fw = fw.replace(" ", "").lower()
            queries.append(
                f'is:issue is:open "{clean_fw}" language:{primary_lang} '
                f'stars:>={min_stars} sort:updated-desc'
            )

    # 7. Performance or testing if requested
    if "performance" in profile.contribution_types:
        queries.append(
            f'is:issue is:open label:"performance","perf" language:{primary_lang} '
            f'stars:>={min_stars} sort:updated-desc'
        )
    elif "testing" in profile.contribution_types:
        queries.append(
            f'is:issue is:open label:"testing","test","tests" language:{primary_lang} '
            f'stars:>={min_stars} sort:updated-desc'
        )

    # Ensure uniqueness and limit total query count
    seen = set()
    deduped: List[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            deduped.append(q)
            if len(deduped) >= max_queries:
                break

    # Fallback default query if list empty
    if not deduped:
        deduped.append(
            f'is:issue is:open label:"good first issue" language:{primary_lang} '
            f'stars:>={min_stars} sort:updated-desc'
        )

    return deduped
