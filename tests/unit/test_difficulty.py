"""Unit tests for difficulty estimation and structured 10-point contribution planning."""

import json
from pathlib import Path
import pytest

from contribscout.analysis.difficulty import (
    estimate_difficulty,
    extract_mentioned_filepaths,
    generate_investigation_plan,
)
from contribscout.discovery.coordinator import normalize_issue, normalize_repository
from contribscout.models import Opportunity, Repository, UserProfile


@pytest.fixture
def fixtures():
    fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
    issues = json.loads((fixtures_dir / "sample_issues.json").read_text(encoding="utf-8"))
    repos = json.loads((fixtures_dir / "sample_repos.json").read_text(encoding="utf-8"))
    return issues, repos


def test_extract_mentioned_filepaths():
    sample_text = """
    We have an error in `src/contribscout/cli.py` and `tests/test_cli.py`.
    See documentation at https://github.com/org/repo/issues/100 and //github.com/files/img.png.
    Another file is model/tokenizer.py line 40.
    """
    paths = extract_mentioned_filepaths(sample_text)
    assert "src/contribscout/cli.py" in paths
    assert "tests/test_cli.py" in paths
    assert "model/tokenizer.py" in paths
    assert not any("github.com" in p for p in paths)
    assert not any("//" in p for p in paths)


def test_estimate_difficulty(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    profile = UserProfile()

    # Typo is beginner
    typo_opp = normalize_issue(issues["typo_documentation"], repo)
    diff_cat, effort, _ = estimate_difficulty(typo_opp, profile)
    assert diff_cat == "Beginner"
    assert "1-3 hours" in effort

    # Bug with traceback is intermediate
    bug_opp = normalize_issue(issues["bug_with_traceback"], repo)
    diff_cat2, effort2, _ = estimate_difficulty(bug_opp, profile)
    assert diff_cat2 in ("Beginner", "Intermediate")


def test_generate_investigation_plan(fixtures):
    issues, repos = fixtures
    repo = normalize_repository(repos["active_repo"], "acme/fast-nlp")
    opp = normalize_issue(issues["bug_with_traceback"], repo)
    profile = UserProfile()

    plan = generate_investigation_plan(opp, profile, "Intermediate")

    # Verify all 10 plan points exist and are populated
    assert plan.problem_summary
    assert plan.importance
    assert len(plan.what_to_read_first) > 0
    assert len(plan.likely_files_or_subsystems) > 0
    assert len(plan.reproduction_steps) > 0
    assert "[Hypothesis]" in plan.implementation_hypothesis
    assert len(plan.test_and_regression_checks) > 0
    assert len(plan.questions_for_maintainers) > 0
    assert len(plan.risks_and_blockers) > 0
    assert plan.suggested_first_action

    # Mentioned file from traceback should be identified
    assert any("tokenizer.py" in f for f in plan.likely_files_or_subsystems)
