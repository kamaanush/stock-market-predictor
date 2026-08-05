from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PatternResult:
    name: str
    direction: str
    confidence: int


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def candle_body(candle: dict[str, Any]) -> float:
    return abs(
        safe_float(candle.get("close"))
        - safe_float(candle.get("open"))
    )


def candle_range(candle: dict[str, Any]) -> float:
    return max(
        safe_float(candle.get("high"))
        - safe_float(candle.get("low")),
        0.0,
    )


def upper_wick(candle: dict[str, Any]) -> float:
    open_price = safe_float(candle.get("open"))
    close_price = safe_float(candle.get("close"))
    high = safe_float(candle.get("high"))

    return max(
        high - max(open_price, close_price),
        0.0,
    )


def lower_wick(candle: dict[str, Any]) -> float:
    open_price = safe_float(candle.get("open"))
    close_price = safe_float(candle.get("close"))
    low = safe_float(candle.get("low"))

    return max(
        min(open_price, close_price) - low,
        0.0,
    )


def is_bullish(candle: dict[str, Any]) -> bool:
    return safe_float(candle.get("close")) > safe_float(
        candle.get("open")
    )


def is_bearish(candle: dict[str, Any]) -> bool:
    return safe_float(candle.get("close")) < safe_float(
        candle.get("open")
    )


def bullish_engulfing(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    previous_open = safe_float(previous.get("open"))
    previous_close = safe_float(previous.get("close"))
    current_open = safe_float(current.get("open"))
    current_close = safe_float(current.get("close"))

    return (
        is_bearish(previous)
        and is_bullish(current)
        and current_open <= previous_close
        and current_close >= previous_open
        and candle_body(current) > candle_body(previous)
    )


def bearish_engulfing(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    previous_open = safe_float(previous.get("open"))
    previous_close = safe_float(previous.get("close"))
    current_open = safe_float(current.get("open"))
    current_close = safe_float(current.get("close"))

    return (
        is_bullish(previous)
        and is_bearish(current)
        and current_open >= previous_close
        and current_close <= previous_open
        and candle_body(current) > candle_body(previous)
    )


def hammer(candle: dict[str, Any]) -> bool:
    body = candle_body(candle)
    full_range = candle_range(candle)
    lower = lower_wick(candle)
    upper = upper_wick(candle)

    if full_range <= 0 or body <= 0:
        return False

    return (
        lower >= body * 2
        and upper <= body * 0.5
        and body / full_range <= 0.4
    )


def shooting_star(candle: dict[str, Any]) -> bool:
    body = candle_body(candle)
    full_range = candle_range(candle)
    lower = lower_wick(candle)
    upper = upper_wick(candle)

    if full_range <= 0 or body <= 0:
        return False

    return (
        upper >= body * 2
        and lower <= body * 0.5
        and body / full_range <= 0.4
    )


def doji(candle: dict[str, Any]) -> bool:
    body = candle_body(candle)
    full_range = candle_range(candle)

    if full_range <= 0:
        return False

    return body / full_range <= 0.1


def inside_bar(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    previous_high = safe_float(previous.get("high"))
    previous_low = safe_float(previous.get("low"))
    current_high = safe_float(current.get("high"))
    current_low = safe_float(current.get("low"))

    return (
        current_high < previous_high
        and current_low > previous_low
    )


def outside_bar(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    previous_high = safe_float(previous.get("high"))
    previous_low = safe_float(previous.get("low"))
    current_high = safe_float(current.get("high"))
    current_low = safe_float(current.get("low"))

    return (
        current_high > previous_high
        and current_low < previous_low
    )


def detect_pattern(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> Optional[PatternResult]:
    if bullish_engulfing(previous, current):
        return PatternResult(
            name="BULLISH ENGULFING",
            direction="BULLISH",
            confidence=90,
        )

    if bearish_engulfing(previous, current):
        return PatternResult(
            name="BEARISH ENGULFING",
            direction="BEARISH",
            confidence=90,
        )

    if hammer(current):
        return PatternResult(
            name="HAMMER",
            direction="BULLISH",
            confidence=75,
        )

    if shooting_star(current):
        return PatternResult(
            name="SHOOTING STAR",
            direction="BEARISH",
            confidence=75,
        )

    if doji(current):
        return PatternResult(
            name="DOJI",
            direction="NEUTRAL",
            confidence=60,
        )

    if outside_bar(previous, current):
        direction = (
            "BULLISH"
            if is_bullish(current)
            else "BEARISH"
            if is_bearish(current)
            else "NEUTRAL"
        )

        return PatternResult(
            name="OUTSIDE BAR",
            direction=direction,
            confidence=70,
        )

    if inside_bar(previous, current):
        return PatternResult(
            name="INSIDE BAR",
            direction="NEUTRAL",
            confidence=65,
        )

    return None