from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RiskResult:
    level: str
    risk_score: int
    reward_risk_ratio: Optional[float]
    stop_distance_percent: Optional[float]
    target_distance_percent: Optional[float]
    warnings: tuple[str, ...]
    positives: tuple[str, ...]
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


def percentage_distance(
    current_price: float,
    level: Optional[float],
) -> Optional[float]:
    if level is None or current_price <= 0:
        return None

    return (
        abs(current_price - float(level))
        / current_price
        * 100
    )


def evaluate_risk(
    *,
    current_price: float,
    signal: str,
    trend_strength: str,
    momentum_classification: str,
    participation_confirmation: bool,
    location_classification: str,
    action_status: str,
    entry: Optional[float],
    stoploss: Optional[float],
    target2: Optional[float],
) -> RiskResult:
    price = float(current_price)

    normalized_signal = signal.upper()
    normalized_trend = trend_strength.upper()
    normalized_momentum = (
        momentum_classification.upper()
    )
    normalized_location = (
        location_classification.upper()
    )
    normalized_action = action_status.upper()

    risk_score = 50

    warnings: list[str] = []
    positives: list[str] = []

    stop_distance = percentage_distance(
        price,
        stoploss,
    )

    target_distance = percentage_distance(
        price,
        target2,
    )

    reward_risk_ratio: Optional[float] = None

    if (
        entry is not None
        and stoploss is not None
        and target2 is not None
    ):
        entry_value = float(entry)
        stop_value = float(stoploss)
        target_value = float(target2)

        risk_amount = abs(
            entry_value - stop_value
        )

        reward_amount = abs(
            target_value - entry_value
        )

        if risk_amount > 0:
            reward_risk_ratio = round(
                reward_amount / risk_amount,
                2,
            )

    if normalized_trend in {
        "VERY STRONG",
        "STRONG",
    }:
        risk_score -= 15
        positives.append(
            "Trend strength supports the setup"
        )

    elif normalized_trend == "DEVELOPING":
        risk_score += 5
        warnings.append(
            "Trend strength is still developing"
        )

    else:
        risk_score += 20
        warnings.append(
            "Weak trend increases false-signal risk"
        )

    if normalized_momentum in {
        "STRONG",
        "OVERBOUGHT",
        "OVERSOLD",
    }:
        risk_score -= 5
        positives.append(
            "Momentum supports directional movement"
        )

    elif normalized_momentum in {
        "BULLISH PULLBACK",
        "BEARISH RECOVERY",
    }:
        risk_score += 10
        warnings.append(
            "Momentum indicators are not fully aligned"
        )

    elif normalized_momentum == "NEUTRAL":
        risk_score += 5
        warnings.append(
            "Momentum is neutral"
        )

    if participation_confirmation:
        risk_score -= 10
        positives.append(
            "Volume confirms the directional move"
        )

    else:
        risk_score += 10
        warnings.append(
            "Volume does not strongly confirm the move"
        )

    if normalized_location == "FAVORABLE":
        risk_score -= 10
        positives.append(
            "Price location is favorable"
        )

    elif normalized_location == "UNFAVORABLE":
        risk_score += 20
        warnings.append(
            "Price location is unfavorable"
        )

    if normalized_action in {
        "WAIT BREAKOUT",
        "WAIT BREAKDOWN",
    }:
        risk_score += 5
        warnings.append(
            "The trade trigger has not been confirmed"
        )

    elif normalized_action == "EXTENDED":
        risk_score += 25
        warnings.append(
            "Price is extended beyond the ideal entry"
        )

    elif normalized_action == "AVOID":
        risk_score += 30
        warnings.append(
            "Execution conditions do not support a trade"
        )

    elif normalized_action == "ACTIVE":
        risk_score -= 5
        positives.append(
            "The setup is inside the active execution zone"
        )

    if reward_risk_ratio is None:
        risk_score += 10
        warnings.append(
            "Reward-to-risk ratio is unavailable"
        )

    elif reward_risk_ratio >= 2:
        risk_score -= 10
        positives.append(
            f"Reward-to-risk ratio is favorable at "
            f"1:{reward_risk_ratio}"
        )

    elif reward_risk_ratio >= 1.5:
        risk_score -= 5
        positives.append(
            f"Reward-to-risk ratio is acceptable at "
            f"1:{reward_risk_ratio}"
        )

    else:
        risk_score += 15
        warnings.append(
            f"Reward-to-risk ratio is weak at "
            f"1:{reward_risk_ratio}"
        )

    if normalized_signal == "WAIT":
        risk_score += 15
        warnings.append(
            "The engine does not currently have a directional signal"
        )

    risk_score = clamp(risk_score)

    if risk_score <= 25:
        level = "LOW"

    elif risk_score <= 50:
        level = "MEDIUM"

    elif risk_score <= 75:
        level = "HIGH"

    else:
        level = "VERY HIGH"

    warning_text = (
        " + ".join(warnings)
        if warnings
        else "No major warnings"
    )

    positive_text = (
        " + ".join(positives)
        if positives
        else "No strong positive risk factors"
    )

    summary = (
        f"Risk is {level.lower()} with a score of "
        f"{risk_score}/100. "
        f"Positives: {positive_text}. "
        f"Warnings: {warning_text}."
    )

    return RiskResult(
        level=level,
        risk_score=risk_score,
        reward_risk_ratio=reward_risk_ratio,
        stop_distance_percent=(
            round(stop_distance, 3)
            if stop_distance is not None
            else None
        ),
        target_distance_percent=(
            round(target_distance, 3)
            if target_distance is not None
            else None
        ),
        warnings=tuple(warnings),
        positives=tuple(positives),
        summary=summary,
    )