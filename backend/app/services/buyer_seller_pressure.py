from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuyerSellerPressureResult:
    buyers_score: int
    sellers_score: int
    pressure: str
    dominance: str
    volume_ratio: float
    candle_strength: str
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


def evaluate_buyer_seller_pressure(
    *,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    average_volume: float,
    vwap: float,
    ema_status: str,
    supertrend_status: str,
    rsi: float,
    macd_status: str,
) -> BuyerSellerPressureResult:
    open_value = float(open_price)
    high_value = float(high)
    low_value = float(low)
    close_value = float(close)
    volume_value = max(0.0, float(volume))
    average_volume_value = max(
        0.0,
        float(average_volume),
    )
    vwap_value = float(vwap)
    rsi_value = float(rsi)

    ema = ema_status.upper()
    supertrend = supertrend_status.upper()
    macd = macd_status.upper()

    buyers = 0
    sellers = 0
    reasons: list[str] = []

    # -------------------------------------------------
    # 1. VOLUME PRESSURE - MAX 30 POINTS
    # -------------------------------------------------

    if average_volume_value > 0:
        volume_ratio = (
            volume_value
            / average_volume_value
        )
    else:
        volume_ratio = 0.0

    if volume_ratio >= 2.0:
        volume_points = 30
        reasons.append(
            f"Volume is {volume_ratio:.2f}x average"
        )

    elif volume_ratio >= 1.5:
        volume_points = 20
        reasons.append(
            f"Volume is {volume_ratio:.2f}x average"
        )

    elif volume_ratio >= 1.2:
        volume_points = 10
        reasons.append(
            f"Volume is {volume_ratio:.2f}x average"
        )

    else:
        volume_points = 0
        reasons.append(
            "Volume is not significantly above average"
        )

    # -------------------------------------------------
    # 2. CANDLE PRESSURE - MAX 20 POINTS
    # -------------------------------------------------

    candle_range = max(
        high_value - low_value,
        0.0,
    )

    candle_body = abs(
        close_value - open_value
    )

    if candle_range > 0:
        body_ratio = (
            candle_body / candle_range
        )
    else:
        body_ratio = 0.0

    bullish_candle = (
        close_value > open_value
    )

    bearish_candle = (
        close_value < open_value
    )

    close_position = 0.5

    if candle_range > 0:
        close_position = (
            close_value - low_value
        ) / candle_range

    if (
        bullish_candle
        and body_ratio >= 0.60
        and close_position >= 0.75
    ):
        candle_strength = "STRONG BUY"
        buyers += 20

        reasons.append(
            "Strong bullish candle closed near its high"
        )

    elif bullish_candle:
        candle_strength = "BUY"
        buyers += 10

        reasons.append(
            "Bullish candle supports buyers"
        )

    elif (
        bearish_candle
        and body_ratio >= 0.60
        and close_position <= 0.25
    ):
        candle_strength = "STRONG SELL"
        sellers += 20

        reasons.append(
            "Strong bearish candle closed near its low"
        )

    elif bearish_candle:
        candle_strength = "SELL"
        sellers += 10

        reasons.append(
            "Bearish candle supports sellers"
        )

    else:
        candle_strength = "NEUTRAL"

        reasons.append(
            "Candle structure is neutral"
        )

    # Apply volume points in the direction of candle pressure.

    if candle_strength in {
        "STRONG BUY",
        "BUY",
    }:
        buyers += volume_points

    elif candle_strength in {
        "STRONG SELL",
        "SELL",
    }:
        sellers += volume_points

    # -------------------------------------------------
    # 3. VWAP PRESSURE - MAX 20 POINTS
    # -------------------------------------------------

    if close_value > vwap_value:
        buyers += 20

        reasons.append(
            "Price is above VWAP"
        )

    elif close_value < vwap_value:
        sellers += 20

        reasons.append(
            "Price is below VWAP"
        )

    else:
        reasons.append(
            "Price is near VWAP"
        )

    # -------------------------------------------------
    # 4. TREND CONFIRMATION - MAX 15 POINTS
    # -------------------------------------------------

    if ema == "BUY":
        buyers += 8
        reasons.append(
            "EMA structure favors buyers"
        )

    elif ema == "SELL":
        sellers += 8
        reasons.append(
            "EMA structure favors sellers"
        )

    if supertrend == "BUY":
        buyers += 7
        reasons.append(
            "SuperTrend favors buyers"
        )

    elif supertrend == "SELL":
        sellers += 7
        reasons.append(
            "SuperTrend favors sellers"
        )

    # -------------------------------------------------
    # 5. MOMENTUM - MAX 15 POINTS
    # -------------------------------------------------

    if 60 <= rsi_value <= 75:
        buyers += 10

        reasons.append(
            "RSI shows healthy bullish momentum"
        )

    elif rsi_value > 75:
        buyers += 5

        reasons.append(
            "RSI is bullish but overbought"
        )

    elif 25 <= rsi_value <= 40:
        sellers += 10

        reasons.append(
            "RSI shows bearish momentum"
        )

    elif rsi_value < 25:
        sellers += 5

        reasons.append(
            "RSI is bearish but oversold"
        )

    if macd == "BUY":
        buyers += 5

        reasons.append(
            "MACD supports buyers"
        )

    elif macd == "SELL":
        sellers += 5

        reasons.append(
            "MACD supports sellers"
        )

    # -------------------------------------------------
    # NORMALIZE
    # -------------------------------------------------

    buyers = clamp(buyers)
    sellers = clamp(sellers)

    total = buyers + sellers

    if total > 0:
        normalized_buyers = round(
            buyers / total * 100
        )

        normalized_sellers = (
            100 - normalized_buyers
        )
    else:
        normalized_buyers = 50
        normalized_sellers = 50

    difference = abs(
        normalized_buyers
        - normalized_sellers
    )

    if normalized_buyers >= 65:
        pressure = "BUYERS DOMINATING"

    elif normalized_sellers >= 65:
        pressure = "SELLERS DOMINATING"

    else:
        pressure = "BALANCED"

    if difference >= 50:
        dominance = "VERY STRONG"

    elif difference >= 30:
        dominance = "STRONG"

    elif difference >= 15:
        dominance = "MODERATE"

    else:
        dominance = "WEAK"

    summary = (
        f"{pressure.lower()} with "
        f"{dominance.lower()} dominance. "
        f"Buyer strength is "
        f"{normalized_buyers}/100 and "
        f"seller strength is "
        f"{normalized_sellers}/100. "
        f"Evidence: {' + '.join(reasons)}"
    )

    return BuyerSellerPressureResult(
        buyers_score=normalized_buyers,
        sellers_score=normalized_sellers,
        pressure=pressure,
        dominance=dominance,
        volume_ratio=round(
            volume_ratio,
            2,
        ),
        candle_strength=candle_strength,
        summary=summary,
    )