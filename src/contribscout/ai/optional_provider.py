"""Optional AI enrichment providers implementing the provider-independent interface."""

from __future__ import annotations

import logging
import os
from typing import Optional
import requests

from contribscout.ai.interface import AIProvider
from contribscout.models import InvestigationPlan, Opportunity, UserProfile

logger = logging.getLogger(__name__)


class NoOpAIProvider(AIProvider):
    """Default provider: performs zero network calls and returns deterministic baseline plans."""

    @property
    def name(self) -> str:
        return "none"

    def is_available(self) -> bool:
        return True

    def enrich_plan(
        self,
        opportunity: Opportunity,
        profile: UserProfile,
        base_plan: InvestigationPlan,
    ) -> InvestigationPlan:
        return base_plan


class HeuristicLocalProvider(AIProvider):
    """Offline deterministic enrichment using domain-specific heuristics without external API calls."""

    @property
    def name(self) -> str:
        return "heuristic"

    def is_available(self) -> bool:
        return True

    def enrich_plan(
        self,
        opportunity: Opportunity,
        profile: UserProfile,
        base_plan: InvestigationPlan,
    ) -> InvestigationPlan:
        plan = InvestigationPlan.from_dict(base_plan.to_dict())

        # Check for framework-specific hints
        text = (opportunity.title + " " + opportunity.body).lower()

        if "pytest" in text or "fastapi" in text or "asyncio" in text:
            plan.implementation_hypothesis += (
                " [Inferred heuristic]: Check asynchronous task execution, event loop handling, "
                "or test fixture scopes."
            )
        elif "numpy" in text or "pytorch" in text:
            plan.implementation_hypothesis += (
                " [Inferred heuristic]: Verify tensor/array shapes, device placement (CPU/CUDA), "
                "and dtype consistency."
            )

        return plan


class OpenAICompatibleProvider(AIProvider):
    """Provider for OpenAI-compatible HTTP endpoints (e.g., local Ollama, LM Studio, vLLM, OpenAI)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15,
    ):
        self.api_key = api_key or os.environ.get("AI_API_KEY", "")
        self.base_url = base_url or os.environ.get("AI_BASE_URL", "http://localhost:11434/v1")
        self.model = model or os.environ.get("AI_MODEL", "llama3")
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "openai_compatible"

    def is_available(self) -> bool:
        # Check if endpoint URL is configured
        return bool(self.base_url)

    def enrich_plan(
        self,
        opportunity: Opportunity,
        profile: UserProfile,
        base_plan: InvestigationPlan,
    ) -> InvestigationPlan:
        """Call compatible chat completions API with strict safety guardrails."""
        if not self.is_available():
            return base_plan

        prompt = (
            f"You are ContribScout's assistant. Provide a brief 1-sentence hypothesis and 1 suggested test "
            f"for this GitHub issue:\n"
            f"Title: {opportunity.title}\n"
            f"Repository: {opportunity.repo_full_name}\n"
            f"Description: {opportunity.body[:400]}\n"
            f"Constraint: Output concise text only. Prefix inferences with '[Inferred]'."
        )

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"

        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful software engineering assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 150,
                    "temperature": 0.2,
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if content:
                    plan = InvestigationPlan.from_dict(base_plan.to_dict())
                    plan.implementation_hypothesis += f"\n[Inferred AI analysis]: {content}"
                    return plan
        except Exception as exc:
            logger.warning(f"AI enrichment failed gracefully ({exc}). Preserving baseline deterministic plan.")

        return base_plan


def get_ai_provider(provider_type: Optional[str] = None) -> AIProvider:
    """Resolve AI provider based on argument or environment variable."""
    chosen = (provider_type or os.environ.get("AI_PROVIDER", "none")).lower().strip()

    if chosen in ("none", "off", "disabled", ""):
        return NoOpAIProvider()
    elif chosen in ("heuristic", "offline"):
        return HeuristicLocalProvider()
    elif chosen in ("openai", "ollama", "compatible", "openrouter"):
        return OpenAICompatibleProvider()
    else:
        logger.warning(f"Unrecognized AI provider '{chosen}'. Using NoOpAIProvider.")
        return NoOpAIProvider()
