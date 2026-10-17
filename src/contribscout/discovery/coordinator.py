"""Discovery coordinator orchestrating queries, pagination, budget protection, and normalization."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from contribscout.discovery.github_api import GitHubAPIClient, RateLimitExceededError
from contribscout.discovery.github_cli import GitHubCLIClient
from contribscout.discovery.queries import build_search_queries
from contribscout.models import Opportunity, Repository, UserProfile

logger = logging.getLogger(__name__)


def infer_issue_type(title: str, labels: List[str]) -> str:
    """Infer contribution type from issue title and label tags."""
    lower_title = title.lower()
    lower_labels = [lbl.lower() for lbl in labels]

    combined = lower_title + " " + " ".join(lower_labels)

    if any(k in combined for k in ["security", "vulnerability", "cve"]):
        return "security"
    if any(k in combined for k in ["perf", "performance", "speed", "latency", "memory leak", "memory"]):
        return "performance"
    if any(k in combined for k in ["test", "tests", "coverage", "pytest", "unit test", "mock"]):
        return "testing"
    if any(k in combined for k in ["doc", "docs", "documentation", "typo", "readme"]):
        return "documentation"
    if any(k in combined for k in ["dx", "developer experience", "linter", "ci", "workflow"]):
        return "dx"
    if any(k in combined for k in ["refactor", "cleanup", "clean up", "restructure"]):
        return "refactoring"
    if any(k in combined for k in ["feat", "feature", "enhancement", "proposal", "add support"]):
        return "feature"
    if any(k in combined for k in ["bug", "fix", "error", "crash", "fault", "broken", "issue", "fails", "traceback"]):
        return "bug"

    return "bug"  # Default actionable assumption


def normalize_repository(repo_data: Optional[Dict[str, Any]], full_name: str) -> Repository:
    """Normalize raw GitHub repository JSON into a typed Repository model."""
    if not repo_data or not isinstance(repo_data, dict):
        parts = full_name.split("/")
        owner = parts[0] if len(parts) > 1 else ""
        name = parts[1] if len(parts) > 1 else full_name
        return Repository(
            owner=owner,
            name=name,
            full_name=full_name,
            url=f"https://github.com/{full_name}",
        )

    owner_obj = repo_data.get("owner", {})
    owner = owner_obj.get("login", "") if isinstance(owner_obj, dict) else ""
    license_obj = repo_data.get("license") or {}
    license_spdx = license_obj.get("spdx_id") or license_obj.get("name") if isinstance(license_obj, dict) else None

    return Repository(
        owner=owner,
        name=repo_data.get("name", ""),
        full_name=repo_data.get("full_name", full_name),
        description=str(repo_data.get("description") or "").strip(),
        url=repo_data.get("html_url", f"https://github.com/{full_name}"),
        primary_language=str(repo_data.get("language") or "").lower(),
        topics=repo_data.get("topics") or [],
        stars=int(repo_data.get("stargazers_count") or 0),
        forks=int(repo_data.get("forks_count") or 0),
        open_issues_count=int(repo_data.get("open_issues_count") or 0),
        license=license_spdx,
        is_archived=bool(repo_data.get("archived", False)),
        is_fork=bool(repo_data.get("fork", False)),
        created_at=str(repo_data.get("created_at") or ""),
        pushed_at=str(repo_data.get("pushed_at") or ""),
        updated_at=str(repo_data.get("updated_at") or ""),
        has_contributing_guide=False,
    )


def normalize_issue(
    item: Dict[str, Any],
    repo_model: Repository,
) -> Opportunity:
    """Normalize raw issue JSON into typed Opportunity model."""
    repo_full_name = repo_model.full_name
    number = int(item.get("number", 0))
    opp_id = f"{repo_full_name}#{number}"

    # Extract labels
    labels_raw = item.get("labels", [])
    labels: List[str] = []
    for lbl in labels_raw:
        if isinstance(lbl, dict):
            name = lbl.get("name")
            if name:
                labels.append(str(name))
        elif isinstance(lbl, str):
            labels.append(lbl)

    # Extract assignees
    assignees_raw = item.get("assignees", [])
    assignees: List[str] = []
    if isinstance(assignees_raw, list):
        for ass in assignees_raw:
            if isinstance(ass, dict) and "login" in ass:
                assignees.append(ass["login"])
            elif isinstance(ass, str):
                assignees.append(ass)
    single_assignee = item.get("assignee")
    if single_assignee and isinstance(single_assignee, dict) and "login" in single_assignee:
        if single_assignee["login"] not in assignees:
            assignees.append(single_assignee["login"])

    title = str(item.get("title") or "").strip()
    body = str(item.get("body") or "").strip()
    # Treat issue text as untrusted data; sanitize control characters
    title = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", title)
    body = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", body)

    inferred = infer_issue_type(title, labels)

    return Opportunity(
        id=opp_id,
        repo_full_name=repo_full_name,
        number=number,
        title=title,
        body=body,
        url=item.get("html_url", f"https://github.com/{repo_full_name}/issues/{number}"),
        state=str(item.get("state") or "open").lower(),
        labels=labels,
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
        comments_count=int(item.get("comments") or 0),
        assignees=assignees,
        has_pull_request=bool(item.get("pull_request")),
        is_locked=bool(item.get("locked", False)),
        repository=repo_model,
        inferred_type=inferred,
    )


class DiscoveryEngine:
    """Manages the full discovery pipeline across backends."""

    def __init__(
        self,
        backend: str = "auto",
        api_client: Optional[GitHubAPIClient] = None,
        cli_client: Optional[GitHubCLIClient] = None,
    ):
        self.backend_choice = backend
        self.api_client = api_client or GitHubAPIClient()
        self.cli_client = cli_client or GitHubCLIClient()
        self.active_backend = self._resolve_backend()

    def _resolve_backend(self) -> str:
        if self.backend_choice == "gh":
            if self.cli_client.is_available() and self.cli_client.is_authenticated():
                return "gh"
            logger.warning("GitHub CLI backend requested but gh is not authenticated. Falling back to API client.")
            return "github_api"
        elif self.backend_choice == "api":
            return "github_api"
        else:  # auto
            if self.api_client.token:
                return "github_api"
            if self.cli_client.is_available() and self.cli_client.is_authenticated():
                return "gh"
            return "github_api"

    def discover(
        self,
        profile: UserProfile,
        max_candidates: Optional[int] = None,
    ) -> Tuple[List[Opportunity], List[str], Dict[str, Any]]:
        """
        Execute multi-query discovery based on profile.
        Returns: (opportunities, warnings, rate_limit_info)
        """
        target_candidates = max_candidates or profile.max_candidates
        queries = build_search_queries(profile)
        warnings: List[str] = []
        opportunities: List[Opportunity] = []
        seen_ids = set()

        requests_budget = profile.api_budget_requests
        requests_spent = 0

        for query in queries:
            page = 1
            while len(opportunities) < target_candidates and requests_spent < requests_budget:
                try:
                    requests_spent += 1
                    if self.active_backend == "gh":
                        search_res = self.cli_client.search_issues(query, per_page=30, page=page)
                    else:
                        search_res = self.api_client.search_issues(query, per_page=30, page=page)

                    items = search_res.get("items", [])
                    if not items:
                        break

                    for item in items:
                        # Ignore PRs returned in issue searches
                        if item.get("pull_request"):
                            continue

                        repo_url = item.get("repository_url", "")
                        # repository_url format: https://api.github.com/repos/owner/name
                        parts = repo_url.rstrip("/").split("/")
                        full_name = f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else "unknown/unknown"

                        opp_id = f"{full_name}#{item.get('number')}"
                        if opp_id in seen_ids:
                            continue
                        seen_ids.add(opp_id)

                        # Parse owner and repo safely
                        if "/" in full_name:
                            owner, repo_name = full_name.split("/", 1)
                        else:
                            owner, repo_name = "", full_name

                        repo_raw = None
                        cache_key = f"{owner.lower()}/{repo_name.lower()}"
                        is_cached = (
                            cache_key in self.api_client.repo_cache
                            if self.active_backend == "github_api"
                            else cache_key in self.cli_client.repo_cache
                        )

                        if requests_spent < requests_budget or is_cached:
                            if not is_cached:
                                requests_spent += 1
                            try:
                                if self.active_backend == "gh":
                                    repo_raw = self.cli_client.get_repository(owner, repo_name)
                                else:
                                    repo_raw = self.api_client.get_repository(owner, repo_name)
                            except Exception:
                                pass

                        repo_model = normalize_repository(repo_raw, full_name)
                        opp = normalize_issue(item, repo_model)
                        opportunities.append(opp)

                        if len(opportunities) >= target_candidates:
                            break

                    total_count = search_res.get("total_count", 0)
                    if len(items) < 30 or (page * 30) >= total_count:
                        # No more pages for this query
                        break

                    page += 1
                    if profile.rate_limit_pause_seconds > 0:
                        time.sleep(profile.rate_limit_pause_seconds)

                except RateLimitExceededError as rle:
                    warnings.append(str(rle))
                    return opportunities, warnings, self._get_rate_limit_info()
                except Exception as exc:
                    warnings.append(f"Search query '{query}' (page {page}) encountered error: {exc}")
                    break

            if profile.rate_limit_pause_seconds > 0:
                time.sleep(profile.rate_limit_pause_seconds)

        return opportunities, warnings, self._get_rate_limit_info()

    def _get_rate_limit_info(self) -> Dict[str, Any]:
        """Fetch current rate limit status depending on active backend."""
        return (
            self.api_client.get_rate_limit()
            if self.active_backend == "github_api"
            else {"backend": "gh", "authenticated": True}
        )
