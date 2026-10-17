"""Abstract provider-independent interface for optional AI assistance."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from contribscout.models import InvestigationPlan, Opportunity, UserProfile


class AIProvider(ABC):
    """Abstract base class for optional AI enrichment providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the AI provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider credentials/endpoint are configured and reachable."""
        pass

    @abstractmethod
    def enrich_plan(
        self,
        opportunity: Opportunity,
        profile: UserProfile,
        base_plan: InvestigationPlan,
    ) -> InvestigationPlan:
        """
        Enrich an investigation plan with AI interpretation.
        Strict contract:
        - Must never alter base URLs or issue numbers.
        - Must mark inferences explicitly with '[Inferred]'.
        - Must not execute code or trigger network side-effects.
        """
        pass
