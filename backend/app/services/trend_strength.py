from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendStrengthResult:
    classification: str
    direction: str
    score: int
    adx: float
    plus_di: float
    minus_di: float
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


def evaluate_trend_strength(
    *,
    adx: float,
    plus_di: float,
    minus_di: float,
) -> TrendStrengthResult:
    adx_value = float(adx)
    plus_value = float(plus_di)
    minus_value = float(minus_di)

    score = 0
    reasons: list[str] = []

    if adx_value >= 40:
        classification = "VERY STRONG"
        base_strength = 40
        reasons.append(
            f"ADX at {adx_value:.1f} indicates a very strong trend"
        )

    elif adx_value >= 25:
        classification = "STRONG"
        base_strength = 30
        reasons.append(
            f"ADX at {adx_value:.1f} indicates a strong trend"
        )

    elif adx_value >= 20:
        classification = "DEVELOPING"
        base_strength = 15
        reasons.append(
            f"ADX at {adx_value:.1f} indicates a developing trend"
        )

    else:
        classification = "WEAK"
        base_strength = 5
        reasons.append(
            f"ADX at {adx_value:.1f} indicates a weak trend"
        )

    if plus_value > minus_value:
        direction = "BULLISH"
        score += base_strength
        reasons.append(
            f"+DI at {plus_value:.1f} is above "
            f"-DI at {minus_value:.1f}"
        )

    elif minus_value > plus_value:
        direction = "BEARISH"
        score -= base_strength
        reasons.append(
            f"-DI at {minus_value:.1f} is above "
            f"+DI at {plus_value:.1f}"
        )

    else:
        direction = "NEUTRAL"
        reasons.append(
            "+DI and -DI are balanced"
        )

    separation = abs(
        plus_value - minus_value
    )

    if separation >= 10:
        bonus = 15
        reasons.append(
            "Directional separation is high"
        )

    elif separation >= 5:
        bonus = 8
        reasons.append(
            "Directional separation is moderate"
        )

    else:
        bonus = 0
        reasons.append(
            "Directional separation is limited"
        )

    if direction == "BULLISH":
        score += bonus

    elif direction == "BEARISH":
        score -= bonus

    score = clamp(score)

    summary = (
        f"Trend strength is {classification.lower()} "
        f"with {direction.lower()} direction. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return TrendStrengthResult(
        classification=classification,
        direction=direction,
        score=score,
        adx=round(adx_value, 2),
        plus_di=round(plus_value, 2),
        minus_di=round(minus_value, 2),
        summary=summary,
    )