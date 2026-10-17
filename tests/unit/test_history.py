"""Unit tests for local history persistence, cross-run deduplication, and corrupt recovery."""

from pathlib import Path
import pytest

from contribscout.models import Opportunity, OpportunityScore
from contribscout.storage.history import HistoryTracker


@pytest.fixture
def dummy_opp_and_score():
    opp = Opportunity(
        id="owner/repo#10",
        repo_full_name="owner/repo",
        number=10,
        title="Test issue",
        url="https://github.com/owner/repo/issues/10",
    )
    score = OpportunityScore(
        opportunity_id=opp.id,
        final_score=7.0,
        practical_usefulness=7.0,
        feasibility=7.0,
        technical_depth=7.0,
        maintainer_responsiveness=7.0,
        learning_and_portfolio=7.0,
        repository_health=7.0,
    )
    return opp, score


def test_history_first_run(tmp_path, dummy_opp_and_score):
    opp, score = dummy_opp_and_score
    history_file = tmp_path / "history.json"

    tracker = HistoryTracker(filepath=history_file)
    badge, prev_score = tracker.record_scan(opp, score)

    assert badge == "NEW"
    assert prev_score is None
    tracker.save()
    assert history_file.exists()


def test_history_seen_and_updated_transitions(tmp_path, dummy_opp_and_score):
    opp, score = dummy_opp_and_score
    history_file = tmp_path / "history.json"

    tracker = HistoryTracker(filepath=history_file)
    tracker.record_scan(opp, score)
    tracker.save()

    # Re-instantiate from saved file
    tracker2 = HistoryTracker(filepath=history_file)
    # Identical score -> SEEN
    badge, prev_score = tracker2.record_scan(opp, score)
    assert badge == "SEEN"
    assert prev_score == 7.0

    # Score changes significantly (>= 0.5) -> UPDATED
    score.final_score = 8.5
    badge_updated, prev = tracker2.record_scan(opp, score)
    assert badge_updated == "UPDATED"
    assert prev == 7.0


def test_history_corrupt_recovery(tmp_path, dummy_opp_and_score):
    opp, score = dummy_opp_and_score
    history_file = tmp_path / "corrupt_history.json"
    # Write invalid JSON
    history_file.write_text("{this is not valid json!}", encoding="utf-8")

    # Should recover gracefully without crashing
    tracker = HistoryTracker(filepath=history_file)
    assert tracker.entries == {}

    # Should be able to record and save normally
    badge, _ = tracker.record_scan(opp, score)
    assert badge == "NEW"
    tracker.save()
    assert history_file.exists()
