"""Unit tests for opportunity eligibility and diagnostic filtering."""

import json
from pathlib import Path
import pytest

from contribscout.analysis.eligibility import evaluate_eligibility
from contribscout.discovery.coordinator import normalize_issue, normalize_repository
from contribscout.models import Opportunity, Repository, UserProfile


@pytest.fixture
def fixtures():
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    issues = json.loads((fixtures_dir / "sample_issues.json").read_text(encoding="utf-8"))
    repos = json.loads((fixtures_dir / "sample_repos.json").read_text(encoding="utf-8"))
    return issues, repos


def test_eligible_bug_issue(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    profile = UserProfile(min_stars=50)

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is True
    assert verdict.reasons == []


def test_ineligible_closed_issue(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["closed_issue"], repo)
    profile = UserProfile()

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is False
    assert any("closed" in r for r in verdict.reasons)


def test_ineligible_assigned_issue(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["assigned_issue"], repo)
    profile = UserProfile()

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is False
    assert any("assigned to alice_developer" in r for r in verdict.reasons)


def test_ineligible_pr_linked_issue(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["pr_linked_issue"], repo)
    profile = UserProfile()

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is False
    assert any("associated pull request" in r for r in verdict.reasons)


def test_ineligible_archived_repo(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["archived_repo"], "acme/legacy-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    profile = UserProfile()

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is False
    assert any("archived" in r for r in verdict.reasons)


def test_ineligible_bot_spam(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bot_spam_issue"], repo)
    profile = UserProfile()

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is False
    assert any("automated" in r or "bot" in r for r in verdict.reasons)


def test_ineligible_user_exclusions(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    # Exclude organization 'acme'
    profile = UserProfile(exclude_orgs=["acme"])

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is False
    assert any("acme" in r for r in verdict.reasons)


def test_ineligible_locked_issue(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    opp.is_locked = True
    profile = UserProfile()

    verdict = evaluate_eligibility(opp, profile)
    assert verdict.is_eligible is False
    assert any("locked" in r for r in verdict.reasons)


def test_eligibility_stale_penalty_and_max_stars(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)

    # Set issue created 400 days ago with 0 comments
    opp.created_at = "2024-01-01T00:00:00Z"
    opp.comments_count = 0

    profile = UserProfile(max_stars=500)  # repo has 1850 stars
    verdict = evaluate_eligibility(opp, profile)

    # Excluded because stars exceed max_stars
    assert verdict.is_eligible is False
    assert any("exceeds configured maximum" in r for r in verdict.reasons)
    # Stale penalty applied
    assert "stale_no_comments" in verdict.penalties
