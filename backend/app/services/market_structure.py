from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MarketStructureResult:
    bias: str
    score: int
    ema_status: str
    supertrend_status: str
    vwap_status: str
    cpr_position: str
    alignment: str
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


def evaluate_market_structure(
    *,
    ema_status: str,
    supertrend_status: str,
    vwap_status: str,
    cpr_position: Optional[str] = None,
) -> MarketStructureResult:
    ema = ema_status.upper()
    supertrend = supertrend_status.upper()
    vwap = vwap_status.upper()

    cpr = (
        cpr_position.upper()
        if cpr_position
        else "UNKNOWN"
    )

    score = 0
    reasons: list[str] = []

    if ema == "BUY":
        score += 30
        reasons.append("EMA structure is bullish")
    elif ema == "SELL":
        score -= 30
        reasons.append("EMA structure is bearish")
    else:
        reasons.append("EMA structure is neutral")

    if supertrend == "BUY":
        score += 30
        reasons.append("SuperTrend supports buyers")
    elif supertrend == "SELL":
        score -= 30
        reasons.append("SuperTrend supports sellers")
    else:
        reasons.append("SuperTrend is neutral")

    if vwap == "ABOVE":
        score += 20
        reasons.append("Price is above VWAP")
    elif vwap == "BELOW":
        score -= 20
        reasons.append("Price is below VWAP")
    else:
        reasons.append("Price is near VWAP")

    if cpr == "ABOVE CPR":
        score += 20
        reasons.append("Price is above CPR")
    elif cpr == "BELOW CPR":
        score -= 20
        reasons.append("Price is below CPR")
    elif cpr == "INSIDE CPR":
        reasons.append(
            "Price is inside CPR and direction is less clear"
        )
    else:
        reasons.append("CPR position is unavailable")

    score = clamp(score)

    bullish_alignment = (
        ema == "BUY"
        and supertrend == "BUY"
        and vwap == "ABOVE"
    )

    bearish_alignment = (
        ema == "SELL"
        and supertrend == "SELL"
        and vwap == "BELOW"
    )

    if bullish_alignment:
        alignment = "BULLISH ALIGNMENT"
    elif bearish_alignment:
        alignment = "BEARISH ALIGNMENT"
    else:
        alignment = "MIXED ALIGNMENT"

    if score >= 60:
        bias = "BULLISH"
    elif score <= -60:
        bias = "BEARISH"
    elif -20 <= score <= 20:
        bias = "SIDEWAYS"
    else:
        bias = "MIXED"

    summary = (
        f"Market structure is {bias.lower()} with "
        f"{alignment.lower()}. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return MarketStructureResult(
        bias=bias,
        score=score,
        ema_status=ema,
        supertrend_status=supertrend,
        vwap_status=vwap,
        cpr_position=cpr,
        alignment=alignment,
        summary=summary,
    )