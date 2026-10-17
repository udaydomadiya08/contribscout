"""AI subsystem for ContribScout."""

from contribscout.ai.interface import AIProvider
from contribscout.ai.optional_provider import (
    HeuristicLocalProvider,
    NoOpAIProvider,
    OpenAICompatibleProvider,
    get_ai_provider,
)

__all__ = [
    "AIProvider",
    "NoOpAIProvider",
    "HeuristicLocalProvider",
    "OpenAICompatibleProvider",
    "get_ai_provider",
]
