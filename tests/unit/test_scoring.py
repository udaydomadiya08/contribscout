"""Unit tests for explainable 0-10 scoring engine, determinism, and ranking logic."""

import json
from pathlib import Path
import pytest

from contribscout.analysis.scoring import (
    calculate_opportunity_score,
    evaluate_confidence,
    score_feasibility,
    score_learning_and_portfolio,
    score_maintainer_responsiveness,
    score_practical_usefulness,
    score_technical_depth,
)
from contribscout.discovery.coordinator import normalize_issue, normalize_repository
from contribscout.models import Opportunity, Repository, UserProfile


@pytest.fixture
def fixtures():
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    issues = json.loads((fixtures_dir / "sample_issues.json").read_text(encoding="utf-8"))
    repos = json.loads((fixtures_dir / "sample_repos.json").read_text(encoding="utf-8"))
    return issues, repos


def test_determinism(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    profile = UserProfile(languages={"python": "advanced"})

    score1 = calculate_opportunity_score(opp, profile)
    score2 = calculate_opportunity_score(opp, profile)

    assert score1.final_score == score2.final_score
    assert score1.confidence_score == score2.confidence_score
    assert score1.score_breakdown == score2.score_breakdown
    assert score1.justifications == score2.justifications


def test_engineering_bug_outranks_trivial_typo(fixtures):
    """
    CRITICAL REQUIREMENT: An easy typo fix must not automatically outrank
    a substantial and feasible engineering improvement.
    """
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    bug_opp = normalize_issue(issues["bug_with_traceback"], repo)
    typo_opp = normalize_issue(issues["typo_documentation"], repo)

    profile = UserProfile(languages={"python": "advanced"}, experience_level="intermediate")

    bug_score = calculate_opportunity_score(bug_opp, profile)
    typo_score = calculate_opportunity_score(typo_opp, profile)

    # Assert that engineering bug scores substantially higher than typo
    assert bug_score.final_score > typo_score.final_score
    assert bug_score.technical_depth > typo_score.technical_depth
    assert bug_score.practical_usefulness > typo_score.practical_usefulness
    assert typo_score.technical_depth <= 2.0


def test_individual_criteria(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    profile = UserProfile(languages={"python": "advanced"})

    usefulness, use_r = score_practical_usefulness(opp)
    assert 0.0 <= usefulness <= 10.0
    assert "functional bug" in use_r

    feasibility, feas_r = score_feasibility(opp, profile, "Intermediate")
    assert 0.0 <= feasibility <= 10.0
    assert "Strong language proficiency" in feas_r

    tech_depth, tech_r = score_technical_depth(opp, "Intermediate")
    assert 0.0 <= tech_depth <= 10.0

    maintainer, maint_r = score_maintainer_responsiveness(opp)
    assert 0.0 <= maintainer <= 10.0

    learning, learn_r = score_learning_and_portfolio(opp, profile)
    assert 0.0 <= learning <= 10.0


def test_confidence_and_sparse_penalty(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")

    # Detailed issue
    detailed_opp = normalize_issue(issues["bug_with_traceback"], repo)
    conf_score, label, evidence, missing = evaluate_confidence(detailed_opp)
    assert label == "High"
    assert conf_score >= 0.75

    # Sparse issue with no body and missing repo metadata
    sparse_opp = Opportunity(
        id="unknown/unknown#1",
        repo_full_name="unknown/unknown",
        number=1,
        title="fix",
        body="",
        repository=None,
    )
    sparse_conf, sparse_label, _, sparse_missing = evaluate_confidence(sparse_opp)
    assert sparse_label == "Low"
    assert len(sparse_missing) > 0


def test_profile_personalization_impact(fixtures):
    """Different user profiles should produce different rankings/scores."""
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)

    python_expert = UserProfile(languages={"python": "expert"}, hours_per_week=20.0)
    rust_only = UserProfile(languages={"rust": "expert"}, hours_per_week=2.0)

    score_py = calculate_opportunity_score(opp, python_expert)
    score_rust = calculate_opportunity_score(opp, rust_only)

    assert score_py.final_score > score_rust.final_score
    assert score_py.feasibility > score_rust.feasibility


def test_scoring_zero_weights_defensive_fallback(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    profile = UserProfile()

    # Pass all zeros
    zero_weights = {k: 0.0 for k in ["practical_usefulness", "feasibility", "technical_depth", "maintainer_responsiveness", "learning_and_portfolio", "repository_health"]}
    score = calculate_opportunity_score(opp, profile, weights=zero_weights)

    # Should have defensively fallen back to default weights
    assert score.final_score > 0.0
    assert 0.0 <= score.final_score <= 10.0


def test_scoring_boundary_values():
    empty_opp = Opportunity(
        id="empty/empty#0",
        repo_full_name="empty/empty",
        number=0,
        title="",
        body="",
        repository=None,
    )
    profile = UserProfile()
    score = calculate_opportunity_score(empty_opp, profile)

    assert 0.0 <= score.final_score <= 10.0
    assert 0.0 <= score.practical_usefulness <= 10.0
    assert 0.0 <= score.feasibility <= 10.0
    assert 0.0 <= score.technical_depth <= 10.0
    assert 0.0 <= score.maintainer_responsiveness <= 10.0
    assert 0.0 <= score.learning_and_portfolio <= 10.0
    assert 0.0 <= score.repository_health <= 10.0
