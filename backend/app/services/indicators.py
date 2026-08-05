from __future__ import annotations

import numpy as np
import pandas as pd


class Indicators:
    @staticmethod
    def ema(
        dataframe: pd.DataFrame,
        period: int = 20,
    ) -> pd.Series:
        return dataframe["close"].ewm(
            span=period,
            adjust=False,
        ).mean()

    @staticmethod
    def rsi(
        dataframe: pd.DataFrame,
        period: int = 14,
    ) -> pd.Series:
        delta = dataframe["close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        average_gain = gain.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        average_loss = loss.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        relative_strength = average_gain / average_loss.replace(
            0,
            np.nan,
        )

        rsi = 100 - (
            100 / (1 + relative_strength)
        )

        return rsi.fillna(50.0)

    @staticmethod
    def macd(
        dataframe: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        fast_ema = dataframe["close"].ewm(
            span=fast,
            adjust=False,
        ).mean()

        slow_ema = dataframe["close"].ewm(
            span=slow,
            adjust=False,
        ).mean()

        macd_line = fast_ema - slow_ema

        signal_line = macd_line.ewm(
            span=signal,
            adjust=False,
        ).mean()

        histogram = macd_line - signal_line

        return (
            macd_line,
            signal_line,
            histogram,
        )

    @staticmethod
    def vwap(
        dataframe: pd.DataFrame,
    ) -> pd.Series:
        typical_price = (
            dataframe["high"]
            + dataframe["low"]
            + dataframe["close"]
        ) / 3

        volume = dataframe["volume"].fillna(0)

        cumulative_volume = volume.cumsum().replace(
            0,
            np.nan,
        )

        cumulative_value = (
            typical_price * volume
        ).cumsum()

        vwap = cumulative_value / cumulative_volume

        return vwap.fillna(dataframe["close"])

    @staticmethod
    def atr(
        dataframe: pd.DataFrame,
        period: int = 14,
    ) -> pd.Series:
        previous_close = dataframe["close"].shift(1)

        true_range = pd.concat(
            [
                dataframe["high"] - dataframe["low"],
                (
                    dataframe["high"]
                    - previous_close
                ).abs(),
                (
                    dataframe["low"]
                    - previous_close
                ).abs(),
            ],
            axis=1,
        ).max(axis=1)

        return true_range.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

    @staticmethod
    def bollinger_bands(
        dataframe: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        middle_band = dataframe["close"].rolling(
            window=period,
            min_periods=period,
        ).mean()

        standard_deviation = dataframe["close"].rolling(
            window=period,
            min_periods=period,
        ).std(ddof=0)

        upper_band = (
            middle_band
            + standard_deviation * std_dev
        )

        lower_band = (
            middle_band
            - standard_deviation * std_dev
        )

        return (
            upper_band,
            middle_band,
            lower_band,
        )

    @staticmethod
    def supertrend(
        dataframe: pd.DataFrame,
        period: int = 10,
        multiplier: float = 3.0,
    ) -> tuple[pd.Series, pd.Series]:
        if dataframe.empty:
            return (
                pd.Series(dtype=float),
                pd.Series(dtype=bool),
            )

        atr = Indicators.atr(
            dataframe,
            period=period,
        )

        midpoint = (
            dataframe["high"]
            + dataframe["low"]
        ) / 2

        basic_upper_band = (
            midpoint + multiplier * atr
        )

        basic_lower_band = (
            midpoint - multiplier * atr
        )

        final_upper_band = basic_upper_band.copy()
        final_lower_band = basic_lower_band.copy()

        supertrend = pd.Series(
            index=dataframe.index,
            dtype=float,
        )

        direction = pd.Series(
            True,
            index=dataframe.index,
            dtype=bool,
        )

        first_index = dataframe.index[0]

        initial_lower = basic_lower_band.loc[
            first_index
        ]

        supertrend.loc[first_index] = (
            initial_lower
            if pd.notna(initial_lower)
            else dataframe.loc[first_index, "close"]
        )

        for position in range(1, len(dataframe)):
            current_index = dataframe.index[position]
            previous_index = dataframe.index[
                position - 1
            ]

            current_close = dataframe.loc[
                current_index,
                "close",
            ]

            previous_close = dataframe.loc[
                previous_index,
                "close",
            ]

            current_basic_upper = (
                basic_upper_band.loc[current_index]
            )

            current_basic_lower = (
                basic_lower_band.loc[current_index]
            )

            previous_final_upper = (
                final_upper_band.loc[previous_index]
            )

            previous_final_lower = (
                final_lower_band.loc[previous_index]
            )

            if pd.isna(current_basic_upper):
                current_basic_upper = (
                    previous_final_upper
                )

            if pd.isna(current_basic_lower):
                current_basic_lower = (
                    previous_final_lower
                )

            if (
                pd.isna(previous_final_upper)
                or current_basic_upper
                < previous_final_upper
                or previous_close
                > previous_final_upper
            ):
                final_upper_band.loc[
                    current_index
                ] = current_basic_upper
            else:
                final_upper_band.loc[
                    current_index
                ] = previous_final_upper

            if (
                pd.isna(previous_final_lower)
                or current_basic_lower
                > previous_final_lower
                or previous_close
                < previous_final_lower
            ):
                final_lower_band.loc[
                    current_index
                ] = current_basic_lower
            else:
                final_lower_band.loc[
                    current_index
                ] = previous_final_lower

            previous_supertrend = supertrend.loc[
                previous_index
            ]

            if (
                pd.isna(previous_supertrend)
                or previous_supertrend
                == previous_final_upper
            ):
                if (
                    current_close
                    <= final_upper_band.loc[
                        current_index
                    ]
                ):
                    supertrend.loc[
                        current_index
                    ] = final_upper_band.loc[
                        current_index
                    ]

                    direction.loc[
                        current_index
                    ] = False
                else:
                    supertrend.loc[
                        current_index
                    ] = final_lower_band.loc[
                        current_index
                    ]

                    direction.loc[
                        current_index
                    ] = True

            else:
                if (
                    current_close
                    >= final_lower_band.loc[
                        current_index
                    ]
                ):
                    supertrend.loc[
                        current_index
                    ] = final_lower_band.loc[
                        current_index
                    ]

                    direction.loc[
                        current_index
                    ] = True
                else:
                    supertrend.loc[
                        current_index
                    ] = final_upper_band.loc[
                        current_index
                    ]

                    direction.loc[
                        current_index
                    ] = False

        return supertrend, direction

    @staticmethod
    def adx(
        dataframe: pd.DataFrame,
        period: int = 14,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        high = dataframe["high"]
        low = dataframe["low"]
        close = dataframe["close"]

        upward_move = high.diff()
        downward_move = -low.diff()

        plus_dm = upward_move.where(
            (
                upward_move > downward_move
            )
            & (
                upward_move > 0
            ),
            0.0,
        )

        minus_dm = downward_move.where(
            (
                downward_move > upward_move
            )
            & (
                downward_move > 0
            ),
            0.0,
        )

        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (
                    high - previous_close
                ).abs(),
                (
                    low - previous_close
                ).abs(),
            ],
            axis=1,
        ).max(axis=1)

        smoothed_true_range = true_range.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        smoothed_plus_dm = plus_dm.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        smoothed_minus_dm = minus_dm.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        plus_di = (
            100
            * smoothed_plus_dm
            / smoothed_true_range.replace(
                0,
                np.nan,
            )
        )

        minus_di = (
            100
            * smoothed_minus_dm
            / smoothed_true_range.replace(
                0,
                np.nan,
            )
        )

        denominator = (
            plus_di + minus_di
        ).replace(
            0,
            np.nan,
        )

        dx = (
            100
            * (
                plus_di - minus_di
            ).abs()
            / denominator
        )

        adx = dx.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        return (
            adx,
            plus_di,
            minus_di,
        )