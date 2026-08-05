from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SignalResult:
    signal: str
    score: int
    grade: str
    trend: str
    reason: str
    entry_price: Optional[float]
    stoploss: Optional[float]
    target1: Optional[float]
    target2: Optional[float]
    action_status: str


def score_to_grade(score: int) -> str:
    if score >= 95:
        return "A+"

    if score >= 85:
        return "A"

    if score >= 70:
        return "B"

    if score >= 55:
        return "C"

    return "AVOID"


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def safe_bool(
    value: Any,
    default: bool = True,
) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "1",
            "yes",
            "bullish",
            "buy",
        }

    return default


def generate_signal(
    latest: dict[str, Any],
    previous: dict[str, Any],
    pattern_name: Optional[str] = None,
    pattern_direction: Optional[str] = None,
    pattern_confidence: Optional[int] = None,
) -> SignalResult:
    close = safe_float(latest.get("close"))

    previous_high = safe_float(
        previous.get("high"),
        close,
    )

    previous_low = safe_float(
        previous.get("low"),
        close,
    )

    ema_fast = safe_float(
        latest.get("ema_fast")
    )

    ema_slow = safe_float(
        latest.get("ema_slow")
    )

    rsi = safe_float(
        latest.get("rsi"),
        50.0,
    )

    macd = safe_float(
        latest.get("macd")
    )

    macd_signal = safe_float(
        latest.get("macd_signal")
    )

    vwap = safe_float(
        latest.get("vwap"),
        close,
    )

    atr = safe_float(
        latest.get("atr")
    )

    volume = safe_float(
        latest.get("volume")
    )

    average_volume = safe_float(
        latest.get("average_volume")
    )

    supertrend_direction = safe_bool(
        latest.get("supertrend_direction"),
        True,
    )

    score = 50
    reasons: list[str] = []

    bullish_ema = ema_fast > ema_slow
    bearish_ema = ema_fast < ema_slow

    bullish_macd = macd > macd_signal
    bearish_macd = macd < macd_signal

    above_vwap = close > vwap
    below_vwap = close < vwap

    high_volume = (
        average_volume > 0
        and volume >= average_volume * 1.2
    )

    if bullish_ema:
        score += 15
        reasons.append("EMA 9 above EMA 21")

    elif bearish_ema:
        score -= 15
        reasons.append("EMA 9 below EMA 21")

    else:
        reasons.append("EMA neutral")

    if supertrend_direction:
        score += 15
        reasons.append("SuperTrend bullish")

    else:
        score -= 15
        reasons.append("SuperTrend bearish")

    if rsi >= 70:
        score += 5
        reasons.append("RSI overbought")

    elif rsi >= 60:
        score += 10
        reasons.append("RSI strong")

    elif rsi <= 30:
        score -= 5
        reasons.append("RSI oversold")

    elif rsi <= 40:
        score -= 10
        reasons.append("RSI weak")

    else:
        reasons.append("RSI neutral")

    if bullish_macd:
        score += 10
        reasons.append("MACD bullish")

    elif bearish_macd:
        score -= 10
        reasons.append("MACD bearish")

    else:
        reasons.append("MACD neutral")

    if above_vwap:
        score += 10
        reasons.append("Price above VWAP")

    elif below_vwap:
        score -= 10
        reasons.append("Price below VWAP")

    else:
        reasons.append("Price at VWAP")

    if high_volume:
        if bullish_ema and above_vwap:
            score += 10
            reasons.append("High bullish volume")

        elif bearish_ema and below_vwap:
            score -= 10
            reasons.append("High bearish volume")

        else:
            reasons.append(
                "High volume without full confirmation"
            )

    else:
        reasons.append("Normal volume")

    if pattern_name and pattern_direction:
        confidence = pattern_confidence or 0

        if pattern_direction == "BULLISH":
            pattern_points = (
                15
                if confidence >= 85
                else 10
            )

            if (
                bullish_ema
                and above_vwap
                and supertrend_direction
            ):
                score += pattern_points

                reasons.append(
                    f"{pattern_name} bullish confirmation"
                )

            else:
                score += 5

                reasons.append(
                    f"{pattern_name} bullish pattern"
                )

        elif pattern_direction == "BEARISH":
            pattern_points = (
                15
                if confidence >= 85
                else 10
            )

            if (
                bearish_ema
                and below_vwap
                and not supertrend_direction
            ):
                score -= pattern_points

                reasons.append(
                    f"{pattern_name} bearish confirmation"
                )

            else:
                score -= 5

                reasons.append(
                    f"{pattern_name} bearish pattern"
                )

        else:
            reasons.append(
                f"{pattern_name} neutral pattern"
            )

    score = clamp_score(score)

    entry_price: Optional[float] = None
    stoploss: Optional[float] = None
    target1: Optional[float] = None
    target2: Optional[float] = None

    if score >= 70:
        signal = "BUY"
        trend = "BULLISH"

        entry_price = round(
            previous_high,
            2,
        )

        minimum_risk = max(
            atr,
            entry_price - previous_low,
            entry_price * 0.002,
        )

        stoploss = round(
            entry_price - minimum_risk,
            2,
        )

        risk = entry_price - stoploss

        target1 = round(
            entry_price + risk,
            2,
        )

        target2 = round(
            entry_price + (risk * 2),
            2,
        )

        if close < entry_price:
            action_status = "WAIT BREAKOUT"

        elif entry_price <= close <= target1:
            action_status = "ACTIVE"

        else:
            action_status = "EXTENDED"

    elif score <= 30:
        signal = "SELL"
        trend = "BEARISH"

        entry_price = round(
            previous_low,
            2,
        )

        minimum_risk = max(
            atr,
            previous_high - entry_price,
            entry_price * 0.002,
        )

        stoploss = round(
            entry_price + minimum_risk,
            2,
        )

        risk = stoploss - entry_price

        target1 = round(
            entry_price - risk,
            2,
        )

        target2 = round(
            entry_price - (risk * 2),
            2,
        )

        if close > entry_price:
            action_status = "WAIT BREAKDOWN"

        elif target1 <= close <= entry_price:
            action_status = "ACTIVE"

        else:
            action_status = "EXTENDED"

    else:
        signal = "WAIT"
        trend = "SIDEWAYS"
        action_status = "AVOID"

    grade = score_to_grade(score)

    return SignalResult(
        signal=signal,
        score=score,
        grade=grade,
        trend=trend,
        reason=" + ".join(reasons),
        entry_price=entry_price,
        stoploss=stoploss,
        target1=target1,
        target2=target2,
        action_status=action_status,
    )