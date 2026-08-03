from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from .indicators import Indicators
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

    missing_columns = required_columns.difference(dataframe.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing candle columns: {missing}")

    for column in ["open", "high", "low", "close", "volume"]:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.dropna(
        subset=["open", "high", "low", "close"]
    )

    dataframe = dataframe.sort_values("time").reset_index(drop=True)

    if len(dataframe) < MINIMUM_CANDLES:
        raise ValueError("Not enough valid candles after cleaning")

    return dataframe


def calculate_indicators(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result["ema_fast"] = Indicators.ema(result, period=9)
    result["ema_slow"] = Indicators.ema(result, period=21)
    result["rsi"] = Indicators.rsi(result, period=14)

    macd, macd_signal, macd_histogram = Indicators.macd(
        result,
        fast=12,
        slow=26,
        signal=9,
    )

    result["macd"] = macd
    result["macd_signal"] = macd_signal
    result["macd_histogram"] = macd_histogram

    result["vwap"] = Indicators.vwap(result)
    result["atr"] = Indicators.atr(result, period=14)

    result["average_volume"] = (
        result["volume"]
        .rolling(window=20, min_periods=5)
        .mean()
    )

    upper_band, middle_band, lower_band = (
        Indicators.bollinger_bands(
            result,
            period=20,
            std_dev=2,
        )
    )

    result["bollinger_upper"] = upper_band
    result["bollinger_middle"] = middle_band
    result["bollinger_lower"] = lower_band

    return result


def clean_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    output: dict[str, Any] = {}

    for key, value in record.items():
        if pd.isna(value):
            output[key] = 0.0
        elif hasattr(value, "item"):
            output[key] = value.item()
        else:
            output[key] = value

    return output


def scan_candles(
    candles: list[dict[str, Any]],
) -> SignalResult:
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
            "average_volume",
        ]
    )

    if len(usable) < 2:
        raise ValueError(
            "Not enough completed indicator rows to generate a signal"
        )

    latest = clean_record(
        usable.iloc[-1].to_dict()
    )

    previous = clean_record(
        usable.iloc[-2].to_dict()
    )

    return generate_signal(
        latest=latest,
        previous=previous,
    )


def scan_symbol(
    symbol: str,
    candles: list[dict[str, Any]],
) -> dict[str, Any]:
    result = scan_candles(candles)

    return {
        "symbol": symbol.upper(),
        **asdict(result),
    }