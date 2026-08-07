from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BreakoutMonitorResult:
    symbol: str
    direction: str
    status: str

    trigger_price: Optional[float]
    current_price: float

    breakout_confirmed: bool
    volume_confirmed: bool
    buyer_pressure_confirmed: bool
    candle_flow_confirmed: bool
    trend_confirmed: bool

    readiness_score: int
    message: str


def evaluate_breakout_monitor(
    *,
    symbol: str,
    direction: str,
    current_price: float,
    trigger_price: Optional[float],
    readiness_score: int,
    buyer_score: int,
    seller_score: int,
    candle_flow_direction: str,
    candle_flow_strength: str,
    volume_confirmed: bool,
    trend_strength: str,
) -> BreakoutMonitorResult:

    normalized_direction = direction.upper()
    normalized_flow = candle_flow_direction.upper()
    normalized_flow_strength = candle_flow_strength.upper()
    normalized_trend = trend_strength.upper()

    price = float(current_price)

    breakout_confirmed = False

    if trigger_price is not None:
        trigger = float(trigger_price)

        if (
            normalized_direction == "BULLISH"
            and price >= trigger
        ):
            breakout_confirmed = True

        elif (
            normalized_direction == "BEARISH"
            and price <= trigger
        ):
            breakout_confirmed = True

    buyer_pressure_confirmed = False

    if normalized_direction == "BULLISH":
        buyer_pressure_confirmed = (
            buyer_score >= 65
        )

    elif normalized_direction == "BEARISH":
        buyer_pressure_confirmed = (
            seller_score >= 65
        )

    candle_flow_confirmed = False

    if normalized_direction == "BULLISH":
        candle_flow_confirmed = (
            normalized_flow == "BULLISH"
            and normalized_flow_strength
            in {
                "STRONG",
                "VERY STRONG",
            }
        )

    elif normalized_direction == "BEARISH":
        candle_flow_confirmed = (
            normalized_flow == "BEARISH"
            and normalized_flow_strength
            in {
                "STRONG",
                "VERY STRONG",
            }
        )

    trend_confirmed = (
        normalized_trend
        in {
            "STRONG",
            "VERY STRONG",
        }
    )

    confirmations = [
        breakout_confirmed,
        volume_confirmed,
        buyer_pressure_confirmed,
        candle_flow_confirmed,
        trend_confirmed,
    ]

    confirmation_count = sum(
        1
        for item in confirmations
        if item
    )

    if (
        breakout_confirmed
        and confirmation_count >= 4
        and readiness_score >= 80
    ):
        status = "BREAKOUT CONFIRMED"

    elif (
        breakout_confirmed
        and confirmation_count >= 3
    ):
        status = "BREAKOUT - WEAK CONFIRMATION"

    elif readiness_score >= 85:
        status = "WATCH CLOSELY"

    elif readiness_score >= 70:
        status = "WATCH BREAKOUT"

    else:
        status = "NO ALERT"

    message = (
        f"{symbol.upper()} "
        f"{normalized_direction.lower()} setup: "
        f"{status}. "
        f"Price={price:.2f}, "
        f"trigger="
        f"{trigger_price if trigger_price is not None else 'N/A'}, "
        f"readiness={readiness_score}, "
        f"confirmations={confirmation_count}/5."
    )

    return BreakoutMonitorResult(
        symbol=symbol.upper(),
        direction=normalized_direction,
        status=status,
        trigger_price=trigger_price,
        current_price=price,
        breakout_confirmed=breakout_confirmed,
        volume_confirmed=volume_confirmed,
        buyer_pressure_confirmed=(
            buyer_pressure_confirmed
        ),
        candle_flow_confirmed=(
            candle_flow_confirmed
        ),
        trend_confirmed=trend_confirmed,
        readiness_score=int(
            readiness_score
        ),
        message=message,
    )