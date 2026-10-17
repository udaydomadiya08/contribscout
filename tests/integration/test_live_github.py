"""Optional live GitHub integration tests. Disabled by default unless RUN_LIVE_GITHUB_TESTS=1."""

import os
import pytest

from contribscout.discovery.github_api import GitHubAPIClient
from contribscout.discovery.coordinator import DiscoveryEngine
from contribscout.models import UserProfile

LIVE_OPT_IN = os.environ.get("RUN_LIVE_GITHUB_TESTS") == "1"


@pytest.mark.skipif(not LIVE_OPT_IN, reason="Live GitHub tests require RUN_LIVE_GITHUB_TESTS=1")
def test_live_github_rate_limit():
    client = GitHubAPIClient()
    limits = client.get_rate_limit()
    assert limits.get("core_limit") is not None
    assert limits.get("core_remaining") is not None


@pytest.mark.skipif(not LIVE_OPT_IN, reason="Live GitHub tests require RUN_LIVE_GITHUB_TESTS=1")
def test_live_github_issue_fetch():
    client = GitHubAPIClient()
    # Query well-known public issue in python/cpython
    issue = client.get_issue("python", "cpython", 1)
    assert issue is not None
    assert issue.get("number") == 1
