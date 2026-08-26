from __future__ import annotations
from .cpr import calculate_cpr
from dataclasses import asdict
from typing import Any

import pandas as pd

from .indicators import Indicators
from .patterns import detect_pattern
from .signal_generator import SignalResult, generate_signal


MINIMUM_CANDLES = 30


def candles_to_dataframe(
    candles: list[dict[str, Any]],
) -> pd.DataFrame:
    if len(candles) < MINIMUM_CANDLES:
        raise ValueError(
            f"At least {MINIMUM_CANDLES} candles are required; "
            f"received {len(candles)}"
        )

    dataframe = pd.DataFrame(candles)

    required_columns = {
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    missing_columns = required_columns.difference(
        dataframe.columns
    )

    if missing_columns:
        missing = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"Missing candle columns: {missing}"
        )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe["volume"] = (
        dataframe["volume"].fillna(0)
    )

    dataframe = dataframe.dropna(
        subset=[
            "open",
            "high",
            "low",
            "close",
        ]
    )

    dataframe = dataframe.sort_values(
        "time"
    ).reset_index(drop=True)

    if len(dataframe) < MINIMUM_CANDLES:
        raise ValueError(
            "Not enough valid candles after cleaning"
        )

    return dataframe


def calculate_indicators(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result["ema_fast"] = Indicators.ema(
        result,
        period=9,
    )

    result["ema_slow"] = Indicators.ema(
        result,
        period=21,
    )

    result["rsi"] = Indicators.rsi(
        result,
        period=14,
    )

    (
        macd,
        macd_signal,
        macd_histogram,
    ) = Indicators.macd(
        result,
        fast=12,
        slow=26,
        signal=9,
    )

    result["macd"] = macd
    result["macd_signal"] = macd_signal
    result["macd_histogram"] = macd_histogram

    result["vwap"] = Indicators.vwap(result)

    # ------------------------------------------------------
    # PREVIOUS NSE TRADING SESSION OHLC
    #
    # CPR for an intraday candle must use the completed
    # previous trading day's High / Low / Close.
    # ------------------------------------------------------

    numeric_time = pd.to_numeric(
        result["time"],
        errors="coerce",
    )

    timestamps = pd.to_datetime(
        numeric_time,
        unit="s",
        utc=True,
        errors="coerce",
    )

    fallback_timestamps = pd.to_datetime(
        result["time"],
        utc=True,
        errors="coerce",
    )

    timestamps = timestamps.fillna(
        fallback_timestamps
    )

    session_date = (
        timestamps
        .dt
        .tz_convert(
            "Asia/Kolkata"
        )
        .dt
        .date
    )

    daily_source = pd.DataFrame(
        {
            "session_date":
                session_date,

            "high":
                result["high"],

            "low":
                result["low"],

            "close":
                result["close"],
        },
        index=result.index,
    )

    daily_ohlc = (
        daily_source
        .groupby(
            "session_date",
            sort=True,
        )
        .agg(
            high=(
                "high",
                "max",
            ),
            low=(
                "low",
                "min",
            ),
            close=(
                "close",
                "last",
            ),
        )
    )

    previous_daily_ohlc = (
        daily_ohlc.shift(1)
    )

    result[
        "previous_day_high"
    ] = session_date.map(
        previous_daily_ohlc[
            "high"
        ]
    )

    result[
        "previous_day_low"
    ] = session_date.map(
        previous_daily_ohlc[
            "low"
        ]
    )

    result[
        "previous_day_close"
    ] = session_date.map(
        previous_daily_ohlc[
            "close"
        ]
    )

    result["atr"] = Indicators.atr(
        result,
        period=14,
    )

    (
        supertrend,
        supertrend_direction,
    ) = Indicators.supertrend(
        result,
        period=10,
        multiplier=3.0,
    )

    result["supertrend"] = supertrend
    result["supertrend_direction"] = (
        supertrend_direction
    )

    adx, plus_di, minus_di = Indicators.adx(
        result,
        period=14,
    )

    result["adx"] = adx
    result["plus_di"] = plus_di
    result["minus_di"] = minus_di

    result["average_volume"] = (
        result["volume"]
        .rolling(
            window=20,
            min_periods=5,
        )
        .mean()
    )

    (
        bollinger_upper,
        bollinger_middle,
        bollinger_lower,
    ) = Indicators.bollinger_bands(
        result,
        period=20,
        std_dev=2.0,
    )

    result["bollinger_upper"] = (
        bollinger_upper
    )

    result["bollinger_middle"] = (
        bollinger_middle
    )

    result["bollinger_lower"] = (
        bollinger_lower
    )

    return result


def clean_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    for key, value in record.items():
        if pd.isna(value):
            cleaned[key] = 0.0

        elif hasattr(value, "item"):
            cleaned[key] = value.item()

        else:
            cleaned[key] = value

    return cleaned


def get_usable_dataframe(
    candles: list[dict[str, Any]],
) -> pd.DataFrame:
    dataframe = candles_to_dataframe(candles)
    dataframe = calculate_indicators(dataframe)

    usable = dataframe.dropna(
        subset=[
            "ema_fast",
            "ema_slow",
            "rsi",
            "macd",
            "macd_signal",
            "vwap",
            "atr",
            "supertrend",
            "adx",
            "plus_di",
            "minus_di",
            "average_volume",
        ]
    )

    if len(usable) < 2:
        raise ValueError(
            "Not enough completed indicator rows "
            "to generate a signal"
        )

    return usable


def scan_candles(
    candles: list[dict[str, Any]],
) -> SignalResult:
    usable = get_usable_dataframe(candles)

    latest = clean_record(
        usable.iloc[-1].to_dict()
    )

    previous = clean_record(
        usable.iloc[-2].to_dict()
    )

    pattern_result = detect_pattern(
        previous=previous,
        current=latest,
    )

    return generate_signal(
        latest=latest,
        previous=previous,
        pattern_name=(
            pattern_result.name
            if pattern_result
            else None
        ),
        pattern_direction=(
            pattern_result.direction
            if pattern_result
            else None
        ),
        pattern_confidence=(
            pattern_result.confidence
            if pattern_result
            else None
        ),
    )


def scan_symbol(
    symbol: str,
    candles: list[dict[str, Any]],
) -> dict[str, Any]:
    usable = get_usable_dataframe(candles)

    latest = clean_record(
        usable.iloc[-1].to_dict()
    )

    previous = clean_record(
        usable.iloc[-2].to_dict()
    )
    
    cpr = calculate_cpr(
    previous_high=latest["previous_day_high"],
    previous_low=latest["previous_day_low"],
    previous_close=latest["previous_day_close"],
    current_price=latest["close"],
)

    pattern_result = detect_pattern(
        previous=previous,
        current=latest,
    )

    signal_result = generate_signal(
        latest=latest,
        previous=previous,
        pattern_name=(
            pattern_result.name
            if pattern_result
            else None
        ),
        pattern_direction=(
            pattern_result.direction
            if pattern_result
            else None
        ),
        pattern_confidence=(
            pattern_result.confidence
            if pattern_result
            else None
        ),
    )

    result: dict[str, Any] = {
        "symbol": symbol.upper(),

        **asdict(signal_result),

        "last_price": round(
            float(latest.get("close", 0)),
            2,
        ),

        "ema_fast": round(
            float(latest.get("ema_fast", 0)),
            2,
        ),

        "ema_slow": round(
            float(latest.get("ema_slow", 0)),
            2,
        ),

        "rsi": round(
            float(latest.get("rsi", 0)),
            2,
        ),

        "macd": round(
            float(latest.get("macd", 0)),
            4,
        ),

        "macd_signal": round(
            float(
                latest.get(
                    "macd_signal",
                    0,
                )
            ),
            4,
        ),

        "macd_histogram": round(
            float(
                latest.get(
                    "macd_histogram",
                    0,
                )
            ),
            4,
        ),

        "vwap": round(
            float(latest.get("vwap", 0)),
            2,
        ),

        "atr": round(
            float(latest.get("atr", 0)),
            2,
        ),

        "supertrend": round(
            float(
                latest.get(
                    "supertrend",
                    0,
                )
            ),
            2,
        ),

        "supertrend_direction": bool(
            latest.get(
                "supertrend_direction",
                True,
            )
        ),

        "adx": round(
            float(latest.get("adx", 0)),
            2,
        ),

        "plus_di": round(
            float(latest.get("plus_di", 0)),
            2,
        ),

        "minus_di": round(
            float(latest.get("minus_di", 0)),
            2,
        ),

        "volume": round(
            float(latest.get("volume", 0)),
            2,
        ),

        "average_volume": round(
            float(
                latest.get(
                    "average_volume",
                    0,
                )
            ),
            2,
        ),

        "bollinger_upper": round(
            float(
                latest.get(
                    "bollinger_upper",
                    0,
                )
            ),
            2,
        ),

        "bollinger_middle": round(
            float(
                latest.get(
                    "bollinger_middle",
                    0,
                )
            ),
            2,
        ),

        "bollinger_lower": round(
            float(
                latest.get(
                    "bollinger_lower",
                    0,
                )
            ),
            2,
        ),
        
        "pivot": cpr.pivot,

"cpr_top": cpr.top_central,

"cpr_bottom": cpr.bottom_central,

"cpr_width": cpr.width,

"cpr_width_percent": cpr.width_percent,

"cpr_classification": cpr.classification,

"pivot_position": cpr.position,

        "pattern": None,
        "pattern_direction": None,
        "pattern_confidence": None,

        # Pivot integration will be added after
        # previous-day OHLC is separated correctly.
    }

    if pattern_result:
        result["pattern"] = (
            pattern_result.name
        )

        result["pattern_direction"] = (
            pattern_result.direction
        )

        result["pattern_confidence"] = (
            pattern_result.confidence
        )

    return result

def prepare_scanner_dataframe(
    candles: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Calculate all indicators once for an entire
    historical candle set.

    Backtesting can then read individual historical
    rows without recalculating EMA/RSI/MACD/etc.
    """

    dataframe = candles_to_dataframe(
        candles
    )

    return calculate_indicators(
        dataframe
    )


def scan_symbol_from_dataframe(
    symbol: str,
    dataframe: pd.DataFrame,
    index: int,
) -> dict[str, Any]:
    """
    Generate exactly the same scanner result as
    scan_symbol(), but use indicators that were
    already calculated.

    Only information at `index` and earlier is used.
    """

    if index < 1:
        raise ValueError(
            "At least two historical rows are required"
        )

    if index >= len(dataframe):
        raise ValueError(
            "Scanner index is outside dataframe"
        )

    required = [
        "ema_fast",
        "ema_slow",
        "rsi",
        "macd",
        "macd_signal",
        "vwap",
        "atr",
        "supertrend",
        "adx",
        "plus_di",
        "minus_di",
        "average_volume",
    ]

    usable = (
        dataframe
        .iloc[: index + 1]
        .dropna(
            subset=required
        )
    )

    if len(usable) < 2:
        raise ValueError(
            "Not enough completed indicator rows "
            "to generate a signal"
        )

    latest_row = (
        usable.iloc[-1]
    )

    previous_row = (
        usable.iloc[-2]
    )

    latest = clean_record(
        latest_row.to_dict()
    )

    previous = clean_record(
        previous_row.to_dict()
    )

    cpr = calculate_cpr(
        previous_high=latest["previous_day_high"],
        previous_low=latest["previous_day_low"],
        previous_close=latest["previous_day_close"],
        current_price=latest["close"],
    )

    pattern_result = detect_pattern(
        previous=previous,
        current=latest,
    )

    signal_result = generate_signal(
        latest=latest,
        previous=previous,
        pattern_name=(
            pattern_result.name
            if pattern_result
            else None
        ),
        pattern_direction=(
            pattern_result.direction
            if pattern_result
            else None
        ),
        pattern_confidence=(
            pattern_result.confidence
            if pattern_result
            else None
        ),
    )

    result: dict[str, Any] = {
        "symbol": symbol.upper(),

        **asdict(signal_result),

        "last_price": round(
            float(latest.get("close", 0)),
            2,
        ),

        "ema_fast": round(
            float(latest.get("ema_fast", 0)),
            2,
        ),

        "ema_slow": round(
            float(latest.get("ema_slow", 0)),
            2,
        ),

        "rsi": round(
            float(latest.get("rsi", 0)),
            2,
        ),

        "macd": round(
            float(latest.get("macd", 0)),
            4,
        ),

        "macd_signal": round(
            float(
                latest.get(
                    "macd_signal",
                    0,
                )
            ),
            4,
        ),

        "macd_histogram": round(
            float(
                latest.get(
                    "macd_histogram",
                    0,
                )
            ),
            4,
        ),

        "vwap": round(
            float(latest.get("vwap", 0)),
            2,
        ),

        "atr": round(
            float(latest.get("atr", 0)),
            2,
        ),

        "supertrend": round(
            float(
                latest.get(
                    "supertrend",
                    0,
                )
            ),
            2,
        ),

        "supertrend_direction": bool(
            latest.get(
                "supertrend_direction",
                True,
            )
        ),

        "adx": round(
            float(latest.get("adx", 0)),
            2,
        ),

        "plus_di": round(
            float(latest.get("plus_di", 0)),
            2,
        ),

        "minus_di": round(
            float(latest.get("minus_di", 0)),
            2,
        ),

        "volume": round(
            float(latest.get("volume", 0)),
            2,
        ),

        "average_volume": round(
            float(
                latest.get(
                    "average_volume",
                    0,
                )
            ),
            2,
        ),

        "bollinger_upper": round(
            float(
                latest.get(
                    "bollinger_upper",
                    0,
                )
            ),
            2,
        ),

        "bollinger_middle": round(
            float(
                latest.get(
                    "bollinger_middle",
                    0,
                )
            ),
            2,
        ),

        "bollinger_lower": round(
            float(
                latest.get(
                    "bollinger_lower",
                    0,
                )
            ),
            2,
        ),

        "pivot": cpr.pivot,
        "cpr_top": cpr.top_central,
        "cpr_bottom": cpr.bottom_central,
        "cpr_width": cpr.width,
        "cpr_width_percent": (
            cpr.width_percent
        ),
        "cpr_classification": (
            cpr.classification
        ),
        "pivot_position": cpr.position,

        "pattern": None,
        "pattern_direction": None,
        "pattern_confidence": None,
    }

    if pattern_result:
        result["pattern"] = (
            pattern_result.name
        )

        result[
            "pattern_direction"
        ] = (
            pattern_result.direction
        )

        result[
            "pattern_confidence"
        ] = (
            pattern_result.confidence
        )

    return result