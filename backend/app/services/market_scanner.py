from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MarketOpportunity:
    symbol: str
    signal: str
    confidence: int
    grade: str
    action: str


def rank_opportunities(
    opportunities: Iterable[MarketOpportunity],
) -> list[MarketOpportunity]:

    return sorted(
        opportunities,
        key=lambda item: (
            item.signal != "BUY",
            -item.confidence,
            item.symbol,
        ),
    )