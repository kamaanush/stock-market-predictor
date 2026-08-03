from __future__ import annotations

import pandas as pd


class Indicators:

    @staticmethod
    def ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
        return df["close"].ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = df["close"].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss

        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ):

        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        macd = ema_fast - ema_slow

        signal_line = macd.ewm(span=signal, adjust=False).mean()

        histogram = macd - signal_line

        return macd, signal_line, histogram

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:

        typical = (
            df["high"] +
            df["low"] +
            df["close"]
        ) / 3

        return (
            typical * df["volume"]
        ).cumsum() / df["volume"].cumsum()

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14):

        high_low = df["high"] - df["low"]

        high_close = (
            df["high"] -
            df["close"].shift()
        ).abs()

        low_close = (
            df["low"] -
            df["close"].shift()
        ).abs()

        tr = pd.concat(
            [high_low, high_close, low_close],
            axis=1
        ).max(axis=1)

        atr = tr.rolling(period).mean()

        return atr

    @staticmethod
    def bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: int = 2,
    ):

        sma = df["close"].rolling(period).mean()

        std = df["close"].rolling(period).std()

        upper = sma + std_dev * std

        lower = sma - std_dev * std

        return upper, sma, lower