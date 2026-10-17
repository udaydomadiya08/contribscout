"""Unit tests for discovery queries, API client, rate limiting, and caching."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests

from contribscout.discovery.coordinator import (
    DiscoveryEngine,
    infer_issue_type,
    normalize_issue,
    normalize_repository,
)
from contribscout.discovery.github_api import GitHubAPIClient, GitHubAPIError, RateLimitExceededError
from contribscout.discovery.queries import build_search_queries
from contribscout.models import Repository, UserProfile


@pytest.fixture
def sample_fixtures():
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    issues = json.loads((fixtures_dir / "sample_issues.json").read_text(encoding="utf-8"))
    repos = json.loads((fixtures_dir / "sample_repos.json").read_text(encoding="utf-8"))
    return issues, repos


def test_build_search_queries():
    profile = UserProfile(
        languages={"python": "advanced"},
        frameworks=["fastapi", "pytorch"],
        interests=["ai/ml", "nlp"],
        contribution_types=["bug", "performance"],
        min_stars=100,
        priority_repos=["pallets/flask"],
    )
    queries = build_search_queries(profile)
    assert any("repo:pallets/flask" in q for q in queries)
    assert any("language:python" in q for q in queries)
    assert any("stars:>=100" in q for q in queries)
    assert len(queries) <= 6


def test_infer_issue_type():
    assert infer_issue_type("Memory leak in buffer", ["bug"]) == "performance"
    assert infer_issue_type("Fix typo in readme", ["docs"]) == "documentation"
    assert infer_issue_type("Add pytest test coverage for router", []) == "testing"
    assert infer_issue_type("Vulnerability in parser", ["security"]) == "security"
    assert infer_issue_type("Crash on NoneType input", []) == "bug"


def test_normalize_repository(sample_fixtures):
    _, repos = sample_fixtures
    active = repos["active_repo"]
    repo_model = normalize_repository(active, "acme/fast-nlp")
    assert repo_model.full_name == "acme/fast-nlp"
    assert repo_model.stars == 1850
    assert repo_model.license == "Apache-2.0"
    assert not repo_model.is_archived


def test_normalize_issue(sample_fixtures):
    issues, repos = sample_fixtures
    raw_issue = issues["bug_with_traceback"]
    repo_model = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(raw_issue, repo_model)

    assert opp.id == "acme/fast-nlp#42"
    assert opp.number == 42
    assert "TypeError" in opp.title
    assert "tokenizer.py" in opp.body
    assert opp.state == "open"
    assert "bug" in opp.labels


def test_github_api_client_rate_limit_handling():
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1700000000",
    }
    mock_resp.json.return_value = {"message": "API rate limit exceeded"}
    mock_session.request.return_value = mock_resp

    client = GitHubAPIClient(token="test_token", session=mock_session)
    with pytest.raises(RateLimitExceededError) as exc_info:
        client.search_issues("test")

    assert "rate limit exceeded" in str(exc_info.value).lower()
    assert exc_info.value.reset_timestamp == 1700000000


def test_github_api_repository_caching():
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"X-RateLimit-Remaining": "4999"}
    mock_resp.json.return_value = {"full_name": "acme/cached-repo", "stargazers_count": 500}
    mock_session.request.return_value = mock_resp

    client = GitHubAPIClient(token="test_token", session=mock_session)
    # First call queries session
    repo1 = client.get_repository("acme", "cached-repo")
    # Second call should hit in-memory cache
    repo2 = client.get_repository("acme", "cached-repo")

    assert repo1 == repo2
    assert mock_session.request.call_count == 1  # Only one HTTP request made!


def test_github_api_retry_on_server_error():
    mock_session = MagicMock()
    err_resp = MagicMock(status_code=502, headers={})
    ok_resp = MagicMock(status_code=200, headers={}, json=lambda: {"items": []})

    mock_session.request.side_effect = [err_resp, ok_resp]

    client = GitHubAPIClient(token="test_token", session=mock_session, max_retries=2)
    with patch("time.sleep"):  # Avoid real sleep in tests
        res = client.search_issues("test")
    assert res == {"items": []}
    assert mock_session.request.call_count == 2


def test_github_api_429_retry_after():
    mock_session = MagicMock()
    mock_resp = MagicMock(status_code=429)
    mock_resp.headers = {"Retry-After": "60"}
    mock_resp.json.return_value = {"message": "You have exceeded a secondary rate limit."}
    mock_session.request.return_value = mock_resp

    client = GitHubAPIClient(token="test_token", session=mock_session)
    with pytest.raises(RateLimitExceededError) as exc_info:
        client.search_issues("test")

    assert "rate limit exceeded" in str(exc_info.value).lower()
    assert exc_info.value.reset_timestamp is not None


def test_github_api_client_error_422():
    mock_session = MagicMock()
    mock_resp = MagicMock(status_code=422)
    mock_resp.headers = {}
    mock_resp.json.return_value = {"message": "Validation Failed"}
    mock_session.request.return_value = mock_resp

    client = GitHubAPIClient(token="test_token", session=mock_session)
    with pytest.raises(GitHubAPIError) as exc_info:
        client.search_issues("invalid:::query")

    assert exc_info.value.status_code == 422
    assert "Validation Failed" in str(exc_info.value)


def test_discovery_pagination():
    mock_api = MagicMock()
    # Page 1 returns 30 items
    items_p1 = [{"number": i, "title": f"Issue {i}", "repository_url": "https://api.github.com/repos/org/repo"} for i in range(1, 31)]
    # Page 2 returns 5 items
    items_p2 = [{"number": i, "title": f"Issue {i}", "repository_url": "https://api.github.com/repos/org/repo"} for i in range(31, 36)]

    mock_api.search_issues.side_effect = [
        {"total_count": 35, "items": items_p1},
        {"total_count": 35, "items": items_p2},
    ]
    mock_api.repo_cache = {"org/repo": {"name": "repo", "owner": {"login": "org"}}}
    mock_api.get_repository.return_value = {"name": "repo", "owner": {"login": "org"}}
    mock_api.get_rate_limit.return_value = {"core_remaining": 5000}

    engine = DiscoveryEngine(backend="api", api_client=mock_api)
    profile = UserProfile(max_candidates=35, api_budget_requests=10, rate_limit_pause_seconds=0)

    with patch("contribscout.discovery.coordinator.build_search_queries", return_value=["test_query"]):
        opps, warnings, _ = engine.discover(profile, max_candidates=35)

    assert len(opps) == 35
    assert mock_api.search_issues.call_count == 2
