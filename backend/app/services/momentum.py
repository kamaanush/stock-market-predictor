from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MomentumResult:
    classification: str
    direction: str
    score: int
    rsi: float
    macd_status: str
    summary: str


def clamp(
    value: int,
    minimum: int = -100,
    maximum: int = 100,
) -> int:
    return max(
        minimum,
        min(maximum, value),
    )


def evaluate_momentum(
    *,
    rsi: float,
    macd_status: str,
) -> MomentumResult:
    rsi_value = float(rsi)
    macd = macd_status.upper()

    score = 0
    reasons: list[str] = []

    if rsi_value >= 75:
        rsi_direction = "BULLISH"
        classification = "OVERBOUGHT"
        score += 10
        reasons.append(
            f"RSI at {rsi_value:.1f} is strongly overbought"
        )

    elif rsi_value >= 60:
        rsi_direction = "BULLISH"
        classification = "STRONG"
        score += 20
        reasons.append(
            f"RSI at {rsi_value:.1f} shows strong bullish momentum"
        )

    elif rsi_value <= 25:
        rsi_direction = "BEARISH"
        classification = "OVERSOLD"
        score -= 10
        reasons.append(
            f"RSI at {rsi_value:.1f} is strongly oversold"
        )

    elif rsi_value <= 40:
        rsi_direction = "BEARISH"
        classification = "WEAK"
        score -= 20
        reasons.append(
            f"RSI at {rsi_value:.1f} shows bearish momentum"
        )

    else:
        rsi_direction = "NEUTRAL"
        classification = "NEUTRAL"
        reasons.append(
            f"RSI at {rsi_value:.1f} is neutral"
        )

    if macd == "BUY":
        score += 20
        reasons.append("MACD confirms bullish momentum")

    elif macd == "SELL":
        score -= 20
        reasons.append("MACD confirms bearish momentum")

    else:
        reasons.append("MACD is neutral")

    score = clamp(score)

    if score >= 20:
        direction = "BULLISH"

    elif score <= -20:
        direction = "BEARISH"

    else:
        direction = "MIXED"

    if (
        rsi_direction == "BULLISH"
        and macd == "SELL"
    ):
        classification = "BULLISH PULLBACK"
        direction = "MIXED"

    elif (
        rsi_direction == "BEARISH"
        and macd == "BUY"
    ):
        classification = "BEARISH RECOVERY"
        direction = "MIXED"

    summary = (
        f"Momentum is {classification.lower()} "
        f"with {direction.lower()} direction. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return MomentumResult(
        classification=classification,
        direction=direction,
        score=score,
        rsi=round(rsi_value, 2),
        macd_status=macd,
        summary=summary,
    )