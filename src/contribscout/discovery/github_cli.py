"""GitHub CLI (gh) backend for discovery operations."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class GitHubCLIClient:
    """Alternative discovery client utilizing the official GitHub CLI (`gh`)."""

    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.repo_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def is_available(cls) -> bool:
        """Check if gh CLI is installed and in PATH."""
        return shutil.which("gh") is not None

    @classmethod
    def is_authenticated(cls) -> bool:
        """Check if gh is authenticated with an active session."""
        if not cls.is_available():
            return False
        try:
            res = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def run_gh_api(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute gh api call and return parsed JSON."""
        cmd = ["gh", "api", endpoint]
        if params:
            for k, v in params.items():
                cmd.extend(["-F", f"{k}={v}"])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            if res.returncode != 0:
                raise RuntimeError(f"gh api command failed ({res.returncode}): {res.stderr.strip()}")
            return json.loads(res.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to decode JSON from gh api: {exc}")
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"gh api command timed out after {self.timeout}s.")

    def search_issues(self, query: str, per_page: int = 30, page: int = 1) -> Dict[str, Any]:
        """Search issues using gh api search/issues."""
        return self.run_gh_api(
            "search/issues",
            params={"q": query, "per_page": per_page, "page": page},
        )

    def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch repository details using gh api with cache."""
        cache_key = f"{owner.lower()}/{repo.lower()}"
        if cache_key in self.repo_cache:
            return self.repo_cache[cache_key]

        try:
            data = self.run_gh_api(f"repos/{owner}/{repo}")
            self.repo_cache[cache_key] = data
            return data
        except Exception as exc:
            logger.warning(f"gh api could not fetch repository {cache_key}: {exc}")
            return None

    def get_issue(self, owner: str, repo: str, number: int) -> Optional[Dict[str, Any]]:
        """Fetch issue details using gh api."""
        try:
            return self.run_gh_api(f"repos/{owner}/{repo}/issues/{number}")
        except Exception as exc:
            logger.warning(f"gh api could not fetch issue {owner}/{repo}#{number}: {exc}")
            return None
