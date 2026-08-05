from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DecisionResult:
    signal: str
    confidence: int
    grade: str
    trend_strength: str
    risk_level: str
    action_status: str
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


def calculate_calibrated_confidence(
    *,
    raw_score: int,
    signal: str,
    trend_strength: str,
    ema_status: str,
    supertrend_status: str,
    macd_status: str,
    vwap_status: str,
    volume_status: str,
    action_status: str,
    pattern_direction: Optional[str],
) -> int:
    confidence = raw_score

    bullish_alignment = (
        ema_status == "BUY"
        and supertrend_status == "BUY"
        and vwap_status == "ABOVE"
    )

    bearish_alignment = (
        ema_status == "SELL"
        and supertrend_status == "SELL"
        and vwap_status == "BELOW"
    )

    if signal == "BUY":
        if not bullish_alignment:
            confidence -= 8

        if macd_status == "SELL":
            confidence -= 6

        if pattern_direction == "BEARISH":
            confidence -= 8

    elif signal == "SELL":
        if not bearish_alignment:
            confidence -= 8

        if macd_status == "BUY":
            confidence -= 6

        if pattern_direction == "BULLISH":
            confidence -= 8

    if trend_strength == "WEAK":
        confidence -= 12

    elif trend_strength == "DEVELOPING":
        confidence -= 5

    if volume_status != "HIGH":
        confidence -= 4

    if action_status in {
        "WAIT BREAKOUT",
        "WAIT BREAKDOWN",
    }:
        confidence -= 3

    elif action_status == "EXTENDED":
        confidence -= 12

    elif action_status == "AVOID":
        confidence -= 15

    # Rule-based technical confidence must never look like
    # a guaranteed probability of trade success.
    maximum_confidence = 95

    if trend_strength != "STRONG":
        maximum_confidence = 88

    if action_status in {
        "EXTENDED",
        "AVOID",
    }:
        maximum_confidence = 75

    return clamp(
        round(confidence),
        minimum=5,
        maximum=maximum_confidence,
    )


def evaluate_decision(
    *,
    ema_status: str,
    supertrend_status: str,
    adx: float,
    plus_di: float,
    minus_di: float,
    rsi: float,
    macd_status: str,
    vwap_status: str,
    volume_status: str,
    pivot_position: Optional[str] = None,
    pattern_direction: Optional[str] = None,
    action_status: str = "AVOID",
) -> DecisionResult:
    ema_status = ema_status.upper()
    supertrend_status = supertrend_status.upper()
    macd_status = macd_status.upper()
    vwap_status = vwap_status.upper()
    volume_status = volume_status.upper()
    action_status = action_status.upper()

    normalized_pattern = (
        pattern_direction.upper()
        if pattern_direction
        else None
    )

    raw_score = 50
    reasons: list[str] = []

    if ema_status == "BUY":
        raw_score += 15
        reasons.append("EMA bullish")

    elif ema_status == "SELL":
        raw_score -= 15
        reasons.append("EMA bearish")

    else:
        reasons.append("EMA neutral")

    if supertrend_status == "BUY":
        raw_score += 15
        reasons.append("SuperTrend bullish")

    elif supertrend_status == "SELL":
        raw_score -= 15
        reasons.append("SuperTrend bearish")

    else:
        reasons.append("SuperTrend neutral")

    if adx >= 40:
        trend_strength = "VERY STRONG"

        if plus_di > minus_di:
            raw_score += 12
            reasons.append(
                "ADX confirms very strong bullish direction"
            )

        elif minus_di > plus_di:
            raw_score -= 12
            reasons.append(
                "ADX confirms very strong bearish direction"
            )

        else:
            reasons.append(
                "ADX is very strong but direction is neutral"
            )

    elif adx >= 25:
        trend_strength = "STRONG"

        if plus_di > minus_di:
            raw_score += 10
            reasons.append(
                "ADX confirms bullish direction"
            )

        elif minus_di > plus_di:
            raw_score -= 10
            reasons.append(
                "ADX confirms bearish direction"
            )

        else:
            reasons.append(
                "ADX is strong but direction is neutral"
            )

    elif adx >= 20:
        trend_strength = "DEVELOPING"
        reasons.append("ADX trend developing")

    else:
        trend_strength = "WEAK"
        raw_score -= 10
        reasons.append("ADX weak trend")

    if rsi >= 75:
        raw_score += 2
        reasons.append("RSI strongly overbought")

    elif rsi >= 60:
        raw_score += 10
        reasons.append("RSI bullish momentum")

    elif rsi <= 25:
        raw_score -= 2
        reasons.append("RSI strongly oversold")

    elif rsi <= 40:
        raw_score -= 10
        reasons.append("RSI bearish momentum")

    else:
        reasons.append("RSI neutral")

    if macd_status == "BUY":
        raw_score += 10
        reasons.append("MACD bullish")

    elif macd_status == "SELL":
        raw_score -= 10
        reasons.append("MACD bearish")

    else:
        reasons.append("MACD neutral")

    if vwap_status == "ABOVE":
        raw_score += 10
        reasons.append("Price above VWAP")

    elif vwap_status == "BELOW":
        raw_score -= 10
        reasons.append("Price below VWAP")

    else:
        reasons.append("Price near VWAP")

    if volume_status == "HIGH":
        if (
            ema_status == "BUY"
            and vwap_status == "ABOVE"
        ):
            raw_score += 10
            reasons.append("High bullish volume")

        elif (
            ema_status == "SELL"
            and vwap_status == "BELOW"
        ):
            raw_score -= 10
            reasons.append("High bearish volume")

        else:
            reasons.append(
                "High volume without directional alignment"
            )

    else:
        reasons.append("Normal volume")

    if pivot_position:
        normalized_pivot = pivot_position.upper()

        if normalized_pivot in {
            "ABOVE PIVOT",
            "ABOVE R1",
        }:
            raw_score += 5
            reasons.append(
                f"Pivot position {normalized_pivot}"
            )

        elif normalized_pivot in {
            "BELOW PIVOT",
            "BELOW S1",
        }:
            raw_score -= 5
            reasons.append(
                f"Pivot position {normalized_pivot}"
            )

    if normalized_pattern == "BULLISH":
        raw_score += 10
        reasons.append(
            "Bullish candlestick confirmation"
        )

    elif normalized_pattern == "BEARISH":
        raw_score -= 10
        reasons.append(
            "Bearish candlestick confirmation"
        )

    raw_score = clamp(raw_score)

    if raw_score >= 68:
        signal = "BUY"

    elif raw_score <= 32:
        signal = "SELL"

    else:
        signal = "WAIT"

    confidence = calculate_calibrated_confidence(
        raw_score=raw_score,
        signal=signal,
        trend_strength=trend_strength,
        ema_status=ema_status,
        supertrend_status=supertrend_status,
        macd_status=macd_status,
        vwap_status=vwap_status,
        volume_status=volume_status,
        action_status=action_status,
        pattern_direction=normalized_pattern,
    )

    if trend_strength == "WEAK":
        risk_level = "HIGH"

    elif action_status in {
        "EXTENDED",
        "AVOID",
    }:
        risk_level = "HIGH"

    elif action_status in {
        "WAIT BREAKOUT",
        "WAIT BREAKDOWN",
    }:
        risk_level = "MEDIUM"

    elif volume_status != "HIGH":
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    grade = confidence_to_grade(confidence)

    summary = (
        f"{signal} setup with "
        f"{trend_strength.lower()} trend. "
        f"Calibrated confidence is {confidence}. "
        f"Risk is {risk_level.lower()}. "
        f"Status: {action_status}. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return DecisionResult(
        signal=signal,
        confidence=confidence,
        grade=grade,
        trend_strength=trend_strength,
        risk_level=risk_level,
        action_status=action_status,
        summary=summary,
    )