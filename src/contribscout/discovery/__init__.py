"""Discovery subsystem for ContribScout."""

from contribscout.discovery.coordinator import DiscoveryEngine
from contribscout.discovery.github_api import GitHubAPIClient, GitHubAPIError, RateLimitExceededError
from contribscout.discovery.github_cli import GitHubCLIClient
from contribscout.discovery.queries import build_search_queries

__all__ = [
    "DiscoveryEngine",
    "GitHubAPIClient",
    "GitHubAPIError",
    "RateLimitExceededError",
    "GitHubCLIClient",
    "build_search_queries",
]
