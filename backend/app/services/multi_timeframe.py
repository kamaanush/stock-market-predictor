from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TimeframeSignal:
    timeframe: str
    signal: str
    confidence: int
    grade: str
    trend: str


@dataclass(frozen=True)
class MultiTimeframeResult:
    signal: str
    confidence: int
    alignment: str

    bullish_count: int
    bearish_count: int
    wait_count: int

    total_timeframes: int

    strongest_timeframe: str

    summary: str

    timeframes: tuple[
        TimeframeSignal,
        ...
    ]


TIMEFRAME_WEIGHTS = {
    "1m": 0.20,
    "5m": 0.35,
    "15m": 0.45,
}


def clamp(
    value: int,
    minimum: int = 0,
    maximum: int = 95,
) -> int:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def normalize_signal(
    value: Any,
) -> str:
    signal = str(
        value or "WAIT"
    ).upper()

    if signal not in {
        "BUY",
        "SELL",
        "WAIT",
    }:
        return "WAIT"

    return signal


def confidence_to_grade(
    confidence: int,
) -> str:
    if confidence >= 90:
        return "A+"

    if confidence >= 85:
        return "A"

    if confidence >= 75:
        return "B"

    if confidence >= 65:
        return "C"

    return "AVOID"


def build_timeframe_signal(
    *,
    timeframe: str,
    result: dict[str, Any],
) -> TimeframeSignal:

    # ---------------------------------------------------------
    # SIGNAL STILL COMES FROM DECISION ENGINE
    # ---------------------------------------------------------

    decision = result.get(
        "decision",
        {},
    )

    signal = normalize_signal(
        decision.get(
            "signal",
            result.get(
                "signal",
                "WAIT",
            ),
        )
    )

    # ---------------------------------------------------------
    # CONFIDENCE NOW COMES FROM MASTER CONFIDENCE ENGINE
    # ---------------------------------------------------------

    master_confidence = result.get(
        "confidence",
        {},
    )

    confidence = int(
        master_confidence.get(
            "confidence",
            decision.get(
                "confidence",
                result.get(
                    "score",
                    0,
                ),
            ),
        )
    )

    grade = str(
        master_confidence.get(
            "grade",
            decision.get(
                "grade",
                result.get(
                    "grade",
                    "AVOID",
                ),
            ),
        )
    )

    # ---------------------------------------------------------
    # TREND
    # ---------------------------------------------------------

    market_structure = result.get(
        "market_structure",
        {},
    )

    trend = str(
        market_structure.get(
            "bias",
            result.get(
                "trend",
                "SIDEWAYS",
            ),
        )
    ).upper()

    return TimeframeSignal(
        timeframe=timeframe,
        signal=signal,
        confidence=confidence,
        grade=grade,
        trend=trend,
    )


def evaluate_multi_timeframe(
    timeframe_results: dict[
        str,
        dict[str, Any],
    ],
) -> MultiTimeframeResult:

    if not timeframe_results:
        raise ValueError(
            "At least one timeframe result is required"
        )

    signals: list[
        TimeframeSignal
    ] = []

    # ---------------------------------------------------------
    # BUILD NORMALIZED TIMEFRAME RESULTS
    # ---------------------------------------------------------

    for timeframe in [
        "1m",
        "5m",
        "15m",
    ]:
        if timeframe not in timeframe_results:
            continue

        signals.append(
            build_timeframe_signal(
                timeframe=timeframe,
                result=timeframe_results[
                    timeframe
                ],
            )
        )

    if not signals:
        raise ValueError(
            "No supported timeframe results were provided"
        )

    # ---------------------------------------------------------
    # COUNTS
    # ---------------------------------------------------------

    bullish_count = sum(
        1
        for item in signals
        if item.signal == "BUY"
    )

    bearish_count = sum(
        1
        for item in signals
        if item.signal == "SELL"
    )

    wait_count = sum(
        1
        for item in signals
        if item.signal == "WAIT"
    )

    # ---------------------------------------------------------
    # WEIGHTED MULTI-TIMEFRAME DIRECTION
    # ---------------------------------------------------------

    weighted_direction = 0.0

    weighted_confidence = 0.0

    total_weight = 0.0

    strongest = signals[0]

    for item in signals:
        weight = TIMEFRAME_WEIGHTS.get(
            item.timeframe,
            0.20,
        )

        total_weight += weight

        # Direction is based on timeframe importance.
        #
        # 1m  = timing
        # 5m  = primary intraday setup
        # 15m = larger intraday context

        if item.signal == "BUY":
            weighted_direction += (
                weight
            )

        elif item.signal == "SELL":
            weighted_direction -= (
                weight
            )

        # Master confidence is now used here.
        weighted_confidence += (
            item.confidence
            * weight
        )

        if (
            item.confidence
            > strongest.confidence
        ):
            strongest = item

    if total_weight <= 0:
        raise ValueError(
            "Invalid timeframe weights"
        )

    direction_score = (
        weighted_direction
        / total_weight
    )

    average_confidence = (
        weighted_confidence
        / total_weight
    )

    # ---------------------------------------------------------
    # FINAL DIRECTION
    # ---------------------------------------------------------

    if direction_score >= 0.45:
        signal = "BUY"

    elif direction_score <= -0.45:
        signal = "SELL"

    else:
        signal = "WAIT"

    # ---------------------------------------------------------
    # ALIGNMENT
    # ---------------------------------------------------------

    total = len(
        signals
    )

    dominant_count = max(
        bullish_count,
        bearish_count,
        wait_count,
    )

    alignment_ratio = (
        dominant_count
        / total
    )

    if alignment_ratio == 1:
        alignment = "FULL"

    elif alignment_ratio >= 0.66:
        alignment = "STRONG"

    elif alignment_ratio >= 0.50:
        alignment = "PARTIAL"

    else:
        alignment = "MIXED"

    # ---------------------------------------------------------
    # MASTER MULTI-TIMEFRAME CONFIDENCE
    # ---------------------------------------------------------

    confidence = (
        average_confidence
    )

    # Only a small alignment adjustment.
    #
    # We do NOT want alignment bonuses to overpower
    # the actual confidence engines.

    if alignment == "FULL":
        confidence += 5

    elif alignment == "STRONG":
        confidence += 2

    elif alignment == "MIXED":
        confidence -= 5

    # ---------------------------------------------------------
    # HIGHER-TIMEFRAME CONFLICT PENALTY
    # ---------------------------------------------------------

    fifteen_minute = next(
        (
            item
            for item in signals
            if item.timeframe
            == "15m"
        ),
        None,
    )

    if fifteen_minute is not None:

        if (
            signal == "BUY"
            and fifteen_minute.signal
            == "SELL"
        ):
            confidence -= 12

        elif (
            signal == "SELL"
            and fifteen_minute.signal
            == "BUY"
        ):
            confidence -= 12

        elif (
            signal
            in {
                "BUY",
                "SELL",
            }
            and fifteen_minute.signal
            == "WAIT"
        ):
            confidence -= 3

    # ---------------------------------------------------------
    # WAIT PENALTY
    # ---------------------------------------------------------

    if signal == "WAIT":
        confidence -= 5

    confidence = clamp(
        round(
            confidence
        )
    )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    timeframe_text = ", ".join(
        (
            f"{item.timeframe}="
            f"{item.signal}"
            f"({item.confidence})"
        )
        for item in signals
    )

    summary = (
        f"Multi-timeframe signal is "
        f"{signal} with "
        f"{alignment.lower()} alignment. "
        f"{bullish_count} bullish, "
        f"{bearish_count} bearish and "
        f"{wait_count} neutral timeframe(s). "
        f"Master confidence is "
        f"{confidence}/100. "
        f"Strongest timeframe is "
        f"{strongest.timeframe} at "
        f"{strongest.confidence} confidence. "
        f"Timeframes: "
        f"{timeframe_text}."
    )

    return MultiTimeframeResult(
        signal=signal,
        confidence=confidence,
        alignment=alignment,

        bullish_count=(
            bullish_count
        ),

        bearish_count=(
            bearish_count
        ),

        wait_count=(
            wait_count
        ),

        total_timeframes=(
            total
        ),

        strongest_timeframe=(
            strongest.timeframe
        ),

        summary=summary,

        timeframes=tuple(
            signals
        ),
    )