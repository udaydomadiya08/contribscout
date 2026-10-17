"""Unit tests for optional AI integration and safety guardrails."""

from unittest.mock import MagicMock, patch
import pytest

from contribscout.ai.interface import AIProvider
from contribscout.ai.optional_provider import (
    HeuristicLocalProvider,
    NoOpAIProvider,
    OpenAICompatibleProvider,
    get_ai_provider,
)
from contribscout.models import InvestigationPlan, Opportunity, UserProfile


@pytest.fixture
def dummy_data():
    opp = Opportunity(
        id="acme/test#1",
        repo_full_name="acme/test",
        number=1,
        title="Asyncio event loop error in fastapi route",
        body="Detailed traceback in router.py with pytest fixture.",
    )
    profile = UserProfile()
    plan = InvestigationPlan(
        problem_summary="Problem summary",
        importance="Importance",
        what_to_read_first=["Read docs"],
        likely_files_or_subsystems=["router.py"],
        reproduction_steps=["Run test"],
        implementation_hypothesis="[Hypothesis]: Fix event loop closing.",
        test_and_regression_checks=["pytest"],
        questions_for_maintainers=["None"],
        risks_and_blockers=["None"],
        suggested_first_action="Check router.py",
    )
    return opp, profile, plan


def test_noop_provider(dummy_data):
    opp, profile, plan = dummy_data
    provider = NoOpAIProvider()
    enriched = provider.enrich_plan(opp, profile, plan)
    assert enriched.implementation_hypothesis == plan.implementation_hypothesis


def test_heuristic_provider(dummy_data):
    opp, profile, plan = dummy_data
    provider = HeuristicLocalProvider()
    enriched = provider.enrich_plan(opp, profile, plan)
    assert "Inferred heuristic" in enriched.implementation_hypothesis


def test_openai_compatible_provider_graceful_failure(dummy_data):
    opp, profile, plan = dummy_data
    # Unreachable base URL to simulate offline / unavailable AI service
    provider = OpenAICompatibleProvider(base_url="http://127.0.0.1:99999/v1", timeout=1)

    # Should fall back to base plan without throwing an unhandled exception
    enriched = provider.enrich_plan(opp, profile, plan)
    assert enriched.problem_summary == plan.problem_summary


def test_get_ai_provider_factory():
    assert isinstance(get_ai_provider("none"), NoOpAIProvider)
    assert isinstance(get_ai_provider("heuristic"), HeuristicLocalProvider)
    assert isinstance(get_ai_provider("openai"), OpenAICompatibleProvider)
