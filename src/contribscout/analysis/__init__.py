"""Analysis subsystem for ContribScout."""

from contribscout.analysis.deduplication import deduplicate_opportunities
from contribscout.analysis.difficulty import estimate_difficulty, generate_investigation_plan
from contribscout.analysis.eligibility import evaluate_eligibility
from contribscout.analysis.repository_health import calculate_repository_health
from contribscout.analysis.scoring import calculate_opportunity_score

__all__ = [
    "deduplicate_opportunities",
    "estimate_difficulty",
    "generate_investigation_plan",
    "evaluate_eligibility",
    "calculate_repository_health",
    "calculate_opportunity_score",
]
