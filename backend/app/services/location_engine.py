from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LocationResult:
    classification: str
    score: int
    cpr_position: str
    trade_location: str
    distance_to_entry_percent: Optional[float]
    distance_to_target1_percent: Optional[float]
    distance_to_stoploss_percent: Optional[float]
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


def percentage_distance(
    current_price: float,
    level: Optional[float],
) -> Optional[float]:
    if level is None or current_price <= 0:
        return None

    return abs(
        current_price - float(level)
    ) / current_price * 100


def evaluate_location(
    *,
    current_price: float,
    signal: str,
    cpr_position: str,
    entry: Optional[float],
    stoploss: Optional[float],
    target1: Optional[float],
    target2: Optional[float],
) -> LocationResult:
    price = float(current_price)
    normalized_signal = signal.upper()

    normalized_cpr = (
        cpr_position.upper()
        if cpr_position
        else "UNKNOWN"
    )

    score = 0
    reasons: list[str] = []

    distance_to_entry = percentage_distance(
        price,
        entry,
    )

    distance_to_target1 = percentage_distance(
        price,
        target1,
    )

    distance_to_stoploss = percentage_distance(
        price,
        stoploss,
    )

    if normalized_cpr == "ABOVE CPR":
        score += 20
        reasons.append(
            "Price is above CPR"
        )

    elif normalized_cpr == "BELOW CPR":
        score -= 20
        reasons.append(
            "Price is below CPR"
        )

    elif normalized_cpr == "INSIDE CPR":
        reasons.append(
            "Price is inside CPR and direction is unclear"
        )

    else:
        reasons.append(
            "CPR position is unavailable"
        )

    if entry is None:
        trade_location = "NO ENTRY LEVEL"
        reasons.append(
            "No entry level is available"
        )

    elif normalized_signal == "BUY":
        if price < entry:
            trade_location = "BELOW ENTRY"

            if distance_to_entry is not None:
                if distance_to_entry <= 0.25:
                    score += 15
                    reasons.append(
                        "Price is close to the breakout entry"
                    )

                elif distance_to_entry <= 0.75:
                    score += 8
                    reasons.append(
                        "Price is approaching the breakout entry"
                    )

                else:
                    reasons.append(
                        "Price remains well below the breakout entry"
                    )

        elif target1 is not None and price <= target1:
            trade_location = "ACTIVE BUY ZONE"
            score += 15

            reasons.append(
                "Price is between entry and target 1"
            )

        elif target2 is not None and price <= target2:
            trade_location = "LATE BUY ZONE"
            score -= 5

            reasons.append(
                "Price is beyond target 1 and upside is reduced"
            )

        else:
            trade_location = "EXTENDED BUY"
            score -= 20

            reasons.append(
                "Price is extended beyond the preferred buy zone"
            )

    elif normalized_signal == "SELL":
        if price > entry:
            trade_location = "ABOVE ENTRY"

            if distance_to_entry is not None:
                if distance_to_entry <= 0.25:
                    score -= 15
                    reasons.append(
                        "Price is close to the breakdown entry"
                    )

                elif distance_to_entry <= 0.75:
                    score -= 8
                    reasons.append(
                        "Price is approaching the breakdown entry"
                    )

                else:
                    reasons.append(
                        "Price remains well above the breakdown entry"
                    )

        elif target1 is not None and price >= target1:
            trade_location = "ACTIVE SELL ZONE"
            score -= 15

            reasons.append(
                "Price is between entry and target 1"
            )

        elif target2 is not None and price >= target2:
            trade_location = "LATE SELL ZONE"
            score += 5

            reasons.append(
                "Price is beyond target 1 and downside is reduced"
            )

        else:
            trade_location = "EXTENDED SELL"
            score += 20

            reasons.append(
                "Price is extended beyond the preferred sell zone"
            )

    else:
        trade_location = "NO TRADE ZONE"

        reasons.append(
            "The current signal does not support an active trade"
        )

    score = clamp(score)

    if score >= 25:
        classification = "FAVORABLE"

    elif score <= -25:
        classification = "UNFAVORABLE"

    else:
        classification = "NEUTRAL"

    summary = (
        f"Price location is {classification.lower()} "
        f"with trade location {trade_location.lower()}. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return LocationResult(
        classification=classification,
        score=score,
        cpr_position=normalized_cpr,
        trade_location=trade_location,
        distance_to_entry_percent=(
            round(distance_to_entry, 3)
            if distance_to_entry is not None
            else None
        ),
        distance_to_target1_percent=(
            round(distance_to_target1, 3)
            if distance_to_target1 is not None
            else None
        ),
        distance_to_stoploss_percent=(
            round(distance_to_stoploss, 3)
            if distance_to_stoploss is not None
            else None
        ),
        summary=summary,
    )