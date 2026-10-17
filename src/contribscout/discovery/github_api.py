"""GitHub REST API discovery client with rate limit tracking, caching, and retry logic."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """Base exception for GitHub API failures."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitExceededError(GitHubAPIError):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, message: str, reset_timestamp: Optional[int] = None):
        super().__init__(message, status_code=403)
        self.reset_timestamp = reset_timestamp


def resolve_github_token() -> Optional[str]:
    """
    Safely resolve GitHub authentication token.
    Checks GITHUB_TOKEN, GH_TOKEN, and GitHub CLI (gh auth token).
    Never prints or logs the token.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and token.strip():
        return token.strip()

    # Try gh auth token if gh is available
    if shutil.which("gh"):
        try:
            res = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

    return None


class GitHubAPIClient:
    """Client for querying GitHub REST API with caching, retries, and rate limit tracking."""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: Optional[str] = None,
        timeout: tuple[int, int] = (10, 20),
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
    ):
        self.token = token if token is not None else resolve_github_token()
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.repo_cache: Dict[str, Dict[str, Any]] = {}
        self.requests_made: int = 0
        self.rate_limit_info: Dict[str, Any] = {
            "limit": None,
            "remaining": None,
            "reset": None,
            "authenticated": bool(self.token),
        }

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ContribScout/0.1.0 (Open-Source Contribution Agent)",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _update_rate_limit(self, response: requests.Response) -> None:
        rem = response.headers.get("X-RateLimit-Remaining")
        lim = response.headers.get("X-RateLimit-Limit")
        rst = response.headers.get("X-RateLimit-Reset")
        if rem is not None:
            try:
                self.rate_limit_info["remaining"] = int(rem)
            except ValueError:
                pass
        if lim is not None:
            try:
                self.rate_limit_info["limit"] = int(lim)
            except ValueError:
                pass
        if rst is not None:
            try:
                self.rate_limit_info["reset"] = int(rst)
            except ValueError:
                pass

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform HTTP request with bounded exponential backoff on transient errors."""
        url = endpoint if endpoint.startswith("http") else f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                self.requests_made += 1
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                self._update_rate_limit(resp)

                # Check for rate limiting (HTTP 403 or 429)
                if resp.status_code in (403, 429):
                    body_msg = ""
                    try:
                        body_msg = resp.json().get("message", "")
                    except Exception:
                        pass
                    retry_after = resp.headers.get("Retry-After")
                    is_rate_limit = (
                        resp.status_code == 429
                        or "rate limit" in body_msg.lower()
                        or resp.headers.get("X-RateLimit-Remaining") == "0"
                        or retry_after is not None
                    )
                    if is_rate_limit:
                        rst = self.rate_limit_info.get("reset")
                        if retry_after:
                            try:
                                rst = int(time.time()) + int(retry_after)
                            except ValueError:
                                pass
                        reset_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(rst)) if rst else "soon"
                        raise RateLimitExceededError(
                            f"GitHub API rate limit exceeded. Resets at {reset_str}. "
                            f"{'Consider providing a GITHUB_TOKEN to increase limits.' if not self.token else ''}",
                            reset_timestamp=rst,
                        )

                # Successful response
                if resp.status_code in (200, 201):
                    return resp.json()

                # Client errors (404, 422, etc.)
                if 400 <= resp.status_code < 500:
                    try:
                        err_data = resp.json()
                        msg = err_data.get("message", resp.text)
                    except Exception:
                        msg = resp.text
                    raise GitHubAPIError(f"GitHub API client error ({resp.status_code}): {msg}", status_code=resp.status_code)

                # Server errors (5xx) -> retry with backoff
                if resp.status_code >= 500:
                    last_error = GitHubAPIError(f"GitHub API server error ({resp.status_code})", status_code=resp.status_code)
                    if attempt < self.max_retries:
                        sleep_time = 2**attempt
                        time.sleep(sleep_time)
                        continue

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    sleep_time = 2**attempt
                    time.sleep(sleep_time)
                    continue

        if last_error:
            raise GitHubAPIError(f"Request failed after {self.max_retries} attempts: {last_error}")
        raise GitHubAPIError("Request failed unexpectedly.")

    def search_issues(
        self,
        query: str,
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Search issues using GitHub Search API."""
        return self.request(
            "GET",
            "/search/issues",
            params={"q": query, "per_page": per_page, "page": page},
        )

    def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch repository details with in-memory caching to avoid redundant API calls."""
        cache_key = f"{owner.lower()}/{repo.lower()}"
        if cache_key in self.repo_cache:
            return self.repo_cache[cache_key]

        try:
            data = self.request("GET", f"/repos/{owner}/{repo}")
            self.repo_cache[cache_key] = data
            return data
        except GitHubAPIError as exc:
            logger.warning(f"Failed to fetch repository metadata for {cache_key}: {exc}")
            return None

    def get_issue(self, owner: str, repo: str, number: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific issue by owner, repo name, and issue number."""
        try:
            return self.request("GET", f"/repos/{owner}/{repo}/issues/{number}")
        except GitHubAPIError as exc:
            logger.warning(f"Failed to fetch issue {owner}/{repo}#{number}: {exc}")
            return None

    def get_rate_limit(self) -> Dict[str, Any]:
        """Query current rate limit status."""
        try:
            data = self.request("GET", "/rate_limit")
            core = data.get("resources", {}).get("core", {})
            search = data.get("resources", {}).get("search", {})
            return {
                "core_remaining": core.get("remaining"),
                "core_limit": core.get("limit"),
                "core_reset": core.get("reset"),
                "search_remaining": search.get("remaining"),
                "search_limit": search.get("limit"),
                "search_reset": search.get("reset"),
                "authenticated": bool(self.token),
            }
        except Exception:
            return self.rate_limit_info
