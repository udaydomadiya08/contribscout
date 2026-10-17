"""Deduplication utilities for opportunity lists."""

from __future__ import annotations

from typing import List, Set
from contribscout.models import Opportunity


def deduplicate_opportunities(opportunities: List[Opportunity]) -> List[Opportunity]:
    """
    Remove duplicate opportunities by issue ID ('owner/repo#number')
    while preserving discovery order.
    """
    seen: Set[str] = set()
    unique: List[Opportunity] = []

    for opp in opportunities:
        if opp.id not in seen:
            seen.add(opp.id)
            unique.append(opp)

    return unique
