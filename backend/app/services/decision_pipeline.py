from __future__ import annotations

from dataclasses import dataclass

from .location_engine import LocationResult
from .market_structure import MarketStructureResult
from .momentum import MomentumResult
from .participation import ParticipationResult
from .risk_engine import RiskResult
from .trend_strength import TrendStrengthResult


@dataclass(frozen=True)
class PipelineDecision:
    signal: str
    confidence: int
    grade: str
    action: str
    summary: str


def clamp(
    value: int,
    minimum: int = 0,
    maximum: int = 100,
) -> int:
    return max(
        minimum,
        min(maximum, value),
    )


def confidence_to_grade(
    confidence: int,
) -> str:

    if confidence >= 92:
        return "A+"

    if confidence >= 84:
        return "A"

    if confidence >= 74:
        return "B"

    if confidence >= 62:
        return "C"

    return "AVOID"


def evaluate_pipeline(
    *,
    market: MarketStructureResult,
    trend: TrendStrengthResult,
    momentum: MomentumResult,
    participation: ParticipationResult,
    location: LocationResult,
    risk: RiskResult,
) -> PipelineDecision:

    confidence = 50

    reasons = []

    confidence += market.score * 0.25
    confidence += trend.score * 0.20
    confidence += momentum.score * 0.15
    confidence += participation.score * 0.10
    confidence += location.score * 0.15

    confidence -= risk.risk_score * 0.20

    confidence = clamp(
        round(confidence)
    )

    if (
        market.bias == "BULLISH"
        and trend.direction == "BULLISH"
    ):
        signal = "BUY"

    elif (
        market.bias == "BEARISH"
        and trend.direction == "BEARISH"
    ):
        signal = "SELL"

    else:
        signal = "WAIT"

    if (
        signal == "BUY"
        and location.trade_location == "BELOW ENTRY"
    ):
        action = "WAIT BREAKOUT"

    elif (
        signal == "SELL"
        and location.trade_location == "ABOVE ENTRY"
    ):
        action = "WAIT BREAKDOWN"

    elif signal == "WAIT":
        action = "NO TRADE"

    else:
        action = "ACTIVE"

    reasons.append(
        market.summary
    )

    reasons.append(
        trend.summary
    )

    reasons.append(
        momentum.summary
    )

    reasons.append(
        participation.summary
    )

    reasons.append(
        location.summary
    )

    reasons.append(
        risk.summary
    )

    return PipelineDecision(
        signal=signal,
        confidence=confidence,
        grade=confidence_to_grade(
            confidence
        ),
        action=action,
        summary=" | ".join(
            reasons
        ),
    )