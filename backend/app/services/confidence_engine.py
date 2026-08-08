from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ConfidenceContributor:
    module: str
    impact: int
    max_weight: int
    reason: str


@dataclass(frozen=True)
class ConfidenceResult:
    signal: str
    confidence: int
    grade: str
    probability: str
    positive_score: int
    penalty_score: int
    contributors: Tuple[ConfidenceContributor, ...]
    summary: str


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _grade(score: int) -> str:
    if score >= 90:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 75:
        return "B"
    if score >= 65:
        return "C"
    return "D"


def _probability(score: int) -> str:
    if score >= 90:
        return "VERY HIGH"
    if score >= 80:
        return "HIGH"
    if score >= 70:
        return "MODERATE"
    return "LOW"


def evaluate_confidence(
    *,
    signal: str,

    market_structure_score: int,
    trend_score: int,
    momentum_score: int,

    participation_confirmation: bool,

    buyer_score: int,
    seller_score: int,

    candle_flow_direction: str,
    candle_flow_score: int,

    breakout_readiness_score: int,

    risk_level: str,
) -> ConfidenceResult:

    signal = signal.upper()
    flow_direction = candle_flow_direction.upper()
    risk_level = risk_level.upper()

    contributors: list[ConfidenceContributor] = []

    # --------------------------------------------------
    # MARKET STRUCTURE — MAX 15
    # --------------------------------------------------

    market_impact = round(
        max(0, min(100, market_structure_score))
        * 15
        / 100
    )

    contributors.append(
        ConfidenceContributor(
            module="Market Structure",
            impact=market_impact,
            max_weight=15,
            reason=(
                f"Market structure score is "
                f"{market_structure_score}/100"
            ),
        )
    )

    # --------------------------------------------------
    # TREND — MAX 15
    # --------------------------------------------------

    # Your trend engine currently uses a smaller
    # internal scale, so normalize it to 15.
    trend_impact = round(
        max(0, min(40, trend_score))
        * 15
        / 40
    )

    contributors.append(
        ConfidenceContributor(
            module="Trend Strength",
            impact=trend_impact,
            max_weight=15,
            reason=f"Trend score is {trend_score}",
        )
    )

    # --------------------------------------------------
    # MOMENTUM — MAX 10
    # --------------------------------------------------

    # Momentum may be negative or positive.
    normalized_momentum = max(
        -100,
        min(100, momentum_score),
    )

    if normalized_momentum > 0:
        momentum_impact = round(
            normalized_momentum * 10 / 100
        )
    elif normalized_momentum < 0:
        momentum_impact = round(
            normalized_momentum * 5 / 100
        )
    else:
        momentum_impact = 0

    contributors.append(
        ConfidenceContributor(
            module="Momentum",
            impact=momentum_impact,
            max_weight=10,
            reason=(
                f"Momentum score is "
                f"{momentum_score}"
            ),
        )
    )

    # --------------------------------------------------
    # PARTICIPATION / VOLUME — MAX 10
    # --------------------------------------------------

    participation_impact = (
        10
        if participation_confirmation
        else 3
    )

    contributors.append(
        ConfidenceContributor(
            module="Participation",
            impact=participation_impact,
            max_weight=10,
            reason=(
                "Volume confirms the move"
                if participation_confirmation
                else "Volume confirmation is limited"
            ),
        )
    )

    # --------------------------------------------------
    # BUYER / SELLER PRESSURE — MAX 15
    # --------------------------------------------------

    pressure_score = 50

    if signal == "BUY":
        pressure_score = buyer_score

    elif signal == "SELL":
        pressure_score = seller_score

    pressure_impact = round(
        max(0, min(100, pressure_score))
        * 15
        / 100
    )

    contributors.append(
        ConfidenceContributor(
            module="Buyer/Seller Pressure",
            impact=pressure_impact,
            max_weight=15,
            reason=(
                f"Directional pressure score is "
                f"{pressure_score}/100"
            ),
        )
    )

    # --------------------------------------------------
    # CANDLE FLOW — MAX 10
    # --------------------------------------------------

    expected_flow = (
        "BULLISH"
        if signal == "BUY"
        else "BEARISH"
        if signal == "SELL"
        else "MIXED"
    )

    if flow_direction == expected_flow:
        flow_strength = min(
            100,
            abs(candle_flow_score),
        )

        candle_impact = round(
            flow_strength * 10 / 100
        )

        candle_reason = (
            f"{flow_direction} candle flow "
            f"supports the {signal} setup"
        )

    elif flow_direction == "MIXED":
        candle_impact = 0
        candle_reason = (
            "Candle flow is mixed"
        )

    else:
        candle_impact = -5
        candle_reason = (
            f"{flow_direction} candle flow "
            f"conflicts with the {signal} setup"
        )

    contributors.append(
        ConfidenceContributor(
            module="Candle Flow",
            impact=candle_impact,
            max_weight=10,
            reason=candle_reason,
        )
    )

    # --------------------------------------------------
    # BREAKOUT READINESS — MAX 15
    # --------------------------------------------------

    breakout_impact = round(
        max(
            0,
            min(
                100,
                breakout_readiness_score,
            ),
        )
        * 15
        / 100
    )

    contributors.append(
        ConfidenceContributor(
            module="Breakout Readiness",
            impact=breakout_impact,
            max_weight=15,
            reason=(
                f"Breakout readiness is "
                f"{breakout_readiness_score}/100"
            ),
        )
    )

    # --------------------------------------------------
    # RISK — MAX +10 / PENALTY
    # --------------------------------------------------

    if risk_level == "LOW":
        risk_impact = 10
        risk_reason = "Risk is low"

    elif risk_level == "MEDIUM":
        risk_impact = 5
        risk_reason = "Risk is medium"

    elif risk_level == "HIGH":
        risk_impact = -10
        risk_reason = "Risk is high"

    else:
        risk_impact = 0
        risk_reason = (
            f"Risk level is {risk_level}"
        )

    contributors.append(
        ConfidenceContributor(
            module="Risk",
            impact=risk_impact,
            max_weight=10,
            reason=risk_reason,
        )
    )

    # --------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------

    positive_score = sum(
        item.impact
        for item in contributors
        if item.impact > 0
    )

    penalty_score = abs(
        sum(
            item.impact
            for item in contributors
            if item.impact < 0
        )
    )

    confidence = _clamp(
        sum(
            item.impact
            for item in contributors
        )
    )

    grade = _grade(confidence)
    probability = _probability(confidence)

    strongest = sorted(
        contributors,
        key=lambda item: item.impact,
        reverse=True,
    )[:3]

    strongest_text = ", ".join(
        item.module
        for item in strongest
        if item.impact > 0
    )

    summary = (
        f"{signal} confidence is "
        f"{confidence}/100 ({grade}). "
        f"Probability classification: "
        f"{probability}. "
        f"Strongest contributors: "
        f"{strongest_text or 'none'}."
    )

    return ConfidenceResult(
        signal=signal,
        confidence=confidence,
        grade=grade,
        probability=probability,
        positive_score=positive_score,
        penalty_score=penalty_score,
        contributors=tuple(contributors),
        summary=summary,
    )