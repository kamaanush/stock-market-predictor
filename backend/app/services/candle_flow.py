from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class CandleFlowResult:
    direction: str
    strength: str
    score: int

    higher_highs: int
    higher_lows: int
    lower_highs: int
    lower_lows: int

    bullish_candles: int
    bearish_candles: int

    body_expansion: bool
    volume_building: bool
    momentum_accelerating: bool

    close_quality: str
    wick_pressure: str

    rsi_flow: str
    macd_flow: str
    vwap_flow: str

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


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return default


def trend_from_series(
    values: Optional[list[float]],
    tolerance: float = 0.0,
) -> str:
    if not values or len(values) < 2:
        return "UNKNOWN"

    clean_values = [
        safe_float(value)
        for value in values
    ]

    rising = 0
    falling = 0

    for previous, current in zip(
        clean_values[:-1],
        clean_values[1:],
    ):
        difference = current - previous

        if difference > tolerance:
            rising += 1

        elif difference < -tolerance:
            falling += 1

    if rising > falling:
        return "RISING"

    if falling > rising:
        return "FALLING"

    return "FLAT"


def evaluate_candle_flow(
    *,
    candles: list[dict[str, Any]],
    rsi_values: Optional[list[float]] = None,
    macd_histogram_values: Optional[
        list[float]
    ] = None,
    vwap_values: Optional[
        list[float]
    ] = None,
    lookback: int = 6,
) -> CandleFlowResult:

    if len(candles) < 3:
        raise ValueError(
            "At least 3 candles are required "
            "for candle-flow analysis"
        )

    recent = candles[
        -max(
            3,
            lookback,
        ):
    ]

    score = 0
    reasons: list[str] = []

    higher_highs = 0
    higher_lows = 0
    lower_highs = 0
    lower_lows = 0

    bullish_candles = 0
    bearish_candles = 0

    bodies: list[float] = []
    volumes: list[float] = []

    close_near_high_count = 0
    close_near_low_count = 0

    bullish_lower_wicks = 0
    bearish_upper_wicks = 0

    # -------------------------------------------------
    # ANALYZE EACH CANDLE
    # -------------------------------------------------

    for candle in recent:
        open_price = safe_float(
            candle.get("open")
        )

        high = safe_float(
            candle.get("high")
        )

        low = safe_float(
            candle.get("low")
        )

        close = safe_float(
            candle.get("close")
        )

        volume = max(
            0.0,
            safe_float(
                candle.get(
                    "volume"
                )
            ),
        )

        candle_range = max(
            high - low,
            0.0,
        )

        body = abs(
            close - open_price
        )

        bodies.append(
            body
        )

        volumes.append(
            volume
        )

        if close > open_price:
            bullish_candles += 1

        elif close < open_price:
            bearish_candles += 1

        if candle_range > 0:
            close_position = (
                close - low
            ) / candle_range

            upper_wick = (
                high
                - max(
                    open_price,
                    close,
                )
            )

            lower_wick = (
                min(
                    open_price,
                    close,
                )
                - low
            )

            if close_position >= 0.75:
                close_near_high_count += 1

            elif close_position <= 0.25:
                close_near_low_count += 1

            if lower_wick > upper_wick:
                bullish_lower_wicks += 1

            elif upper_wick > lower_wick:
                bearish_upper_wicks += 1

    # -------------------------------------------------
    # MARKET STRUCTURE
    # -------------------------------------------------

    for previous, current in zip(
        recent[:-1],
        recent[1:],
    ):
        previous_high = safe_float(
            previous.get("high")
        )

        current_high = safe_float(
            current.get("high")
        )

        previous_low = safe_float(
            previous.get("low")
        )

        current_low = safe_float(
            current.get("low")
        )

        if current_high > previous_high:
            higher_highs += 1

        elif current_high < previous_high:
            lower_highs += 1

        if current_low > previous_low:
            higher_lows += 1

        elif current_low < previous_low:
            lower_lows += 1

    bullish_structure = (
        higher_highs
        + higher_lows
    )

    bearish_structure = (
        lower_highs
        + lower_lows
    )

    if bullish_structure > bearish_structure:
        score += 25

        reasons.append(
            "Recent candles are forming "
            "higher highs and/or higher lows"
        )

    elif bearish_structure > bullish_structure:
        score -= 25

        reasons.append(
            "Recent candles are forming "
            "lower highs and/or lower lows"
        )

    else:
        reasons.append(
            "Recent price structure is mixed"
        )

    # -------------------------------------------------
    # CANDLE DIRECTION
    # -------------------------------------------------

    if bullish_candles > bearish_candles:
        score += 15

        reasons.append(
            "Bullish candles dominate "
            "the recent sequence"
        )

    elif bearish_candles > bullish_candles:
        score -= 15

        reasons.append(
            "Bearish candles dominate "
            "the recent sequence"
        )

    else:
        reasons.append(
            "Bullish and bearish candles "
            "are balanced"
        )

    # -------------------------------------------------
    # BODY EXPANSION
    # -------------------------------------------------

    body_expansion = False

    if len(bodies) >= 3:
        early_body_average = (
            sum(
                bodies[:2]
            )
            / 2
        )

        late_body_average = (
            sum(
                bodies[-2:]
            )
            / 2
        )

        if (
            early_body_average > 0
            and late_body_average
            >= early_body_average * 1.25
        ):
            body_expansion = True

            latest_candle = recent[-1]

            latest_open = safe_float(
                latest_candle.get(
                    "open"
                )
            )

            latest_close = safe_float(
                latest_candle.get(
                    "close"
                )
            )

            if latest_close > latest_open:
                score += 10

                reasons.append(
                    "Bullish candle bodies "
                    "are expanding"
                )

            elif latest_close < latest_open:
                score -= 10

                reasons.append(
                    "Bearish candle bodies "
                    "are expanding"
                )

    # -------------------------------------------------
    # VOLUME FLOW
    # -------------------------------------------------

    volume_building = False

    if len(volumes) >= 3:
        recent_volume = (
            sum(
                volumes[-2:]
            )
            / 2
        )

        previous_volume = (
            sum(
                volumes[:2]
            )
            / 2
        )

        if (
            previous_volume > 0
            and recent_volume
            >= previous_volume * 1.15
        ):
            volume_building = True

            if bullish_candles > bearish_candles:
                score += 10

            elif bearish_candles > bullish_candles:
                score -= 10

            reasons.append(
                "Volume is building across "
                "recent candles"
            )

    # -------------------------------------------------
    # CLOSE QUALITY
    # -------------------------------------------------

    if (
        close_near_high_count
        > close_near_low_count
    ):
        close_quality = "BULLISH"

        score += 10

        reasons.append(
            "Recent candles frequently "
            "close near their highs"
        )

    elif (
        close_near_low_count
        > close_near_high_count
    ):
        close_quality = "BEARISH"

        score -= 10

        reasons.append(
            "Recent candles frequently "
            "close near their lows"
        )

    else:
        close_quality = "NEUTRAL"

    # -------------------------------------------------
    # WICK PRESSURE
    # -------------------------------------------------

    if (
        bullish_lower_wicks
        > bearish_upper_wicks
    ):
        wick_pressure = (
            "BUYERS DEFENDING"
        )

        score += 5

        reasons.append(
            "Lower wicks suggest buyers "
            "are defending pullbacks"
        )

    elif (
        bearish_upper_wicks
        > bullish_lower_wicks
    ):
        wick_pressure = (
            "SELLERS REJECTING"
        )

        score -= 5

        reasons.append(
            "Upper wicks suggest sellers "
            "are rejecting higher prices"
        )

    else:
        wick_pressure = "BALANCED"

    # -------------------------------------------------
    # RSI FLOW
    # -------------------------------------------------

    rsi_flow = trend_from_series(
        rsi_values
    )

    if rsi_flow == "RISING":
        score += 10

        reasons.append(
            "RSI is improving"
        )

    elif rsi_flow == "FALLING":
        score -= 10

        reasons.append(
            "RSI is weakening"
        )

    # -------------------------------------------------
    # MACD HISTOGRAM FLOW
    # -------------------------------------------------

    macd_flow = trend_from_series(
        macd_histogram_values
    )

    if macd_flow == "RISING":
        score += 10

        reasons.append(
            "MACD histogram is improving"
        )

    elif macd_flow == "FALLING":
        score -= 10

        reasons.append(
            "MACD histogram is weakening"
        )

    # -------------------------------------------------
    # VWAP FLOW
    # -------------------------------------------------

    vwap_flow = "UNKNOWN"

    if (
        vwap_values
        and len(vwap_values) >= 2
    ):
        recent_closes = [
            safe_float(
                candle.get(
                    "close"
                )
            )
            for candle in recent[
                -len(vwap_values):
            ]
        ]

        usable_count = min(
            len(recent_closes),
            len(vwap_values),
        )

        recent_closes = (
            recent_closes[
                -usable_count:
            ]
        )

        usable_vwap = (
            vwap_values[
                -usable_count:
            ]
        )

        above_count = sum(
            1
            for close, vwap
            in zip(
                recent_closes,
                usable_vwap,
            )
            if close
            > safe_float(vwap)
        )

        below_count = (
            usable_count
            - above_count
        )

        if above_count > below_count:
            vwap_flow = (
                "ABOVE VWAP"
            )

            score += 10

            reasons.append(
                "Recent candles are "
                "holding above VWAP"
            )

        elif below_count > above_count:
            vwap_flow = (
                "BELOW VWAP"
            )

            score -= 10

            reasons.append(
                "Recent candles are "
                "holding below VWAP"
            )

        else:
            vwap_flow = (
                "MIXED"
            )

    # -------------------------------------------------
    # MOMENTUM ACCELERATION
    # -------------------------------------------------

    momentum_accelerating = (
        (
            rsi_flow == "RISING"
            and macd_flow == "RISING"
        )
        or (
            rsi_flow == "FALLING"
            and macd_flow == "FALLING"
        )
    )

    # -------------------------------------------------
    # FINAL CLASSIFICATION
    # -------------------------------------------------

    score = clamp(
        score
    )

    if score >= 55:
        direction = "BULLISH"
        strength = "VERY STRONG"

    elif score >= 30:
        direction = "BULLISH"
        strength = "STRONG"

    elif score >= 15:
        direction = "BULLISH"
        strength = "MODERATE"

    elif score <= -55:
        direction = "BEARISH"
        strength = "VERY STRONG"

    elif score <= -30:
        direction = "BEARISH"
        strength = "STRONG"

    elif score <= -15:
        direction = "BEARISH"
        strength = "MODERATE"

    else:
        direction = "MIXED"
        strength = "WEAK"

    summary = (
        f"Candle flow is "
        f"{direction.lower()} with "
        f"{strength.lower()} strength. "
        f"Score: {score}. "
        f"Evidence: "
        f"{' + '.join(reasons)}"
    )

    return CandleFlowResult(
        direction=direction,
        strength=strength,
        score=score,

        higher_highs=(
            higher_highs
        ),

        higher_lows=(
            higher_lows
        ),

        lower_highs=(
            lower_highs
        ),

        lower_lows=(
            lower_lows
        ),

        bullish_candles=(
            bullish_candles
        ),

        bearish_candles=(
            bearish_candles
        ),

        body_expansion=(
            body_expansion
        ),

        volume_building=(
            volume_building
        ),

        momentum_accelerating=(
            momentum_accelerating
        ),

        close_quality=(
            close_quality
        ),

        wick_pressure=(
            wick_pressure
        ),

        rsi_flow=(
            rsi_flow
        ),

        macd_flow=(
            macd_flow
        ),

        vwap_flow=(
            vwap_flow
        ),

        summary=summary,
    )