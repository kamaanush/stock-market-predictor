from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional


class LiveCandleEngine:
    """
    Builds live OHLCV candles from market ticks.

    Base timeframe:
        1 minute

    Derived timeframes:
        5 minutes
        15 minutes
    """

    def __init__(
        self,
        max_candles: int = 500,
    ) -> None:

        self.max_candles = max_candles

        # Structure:
        #
        # {
        #     "SBIN": {
        #         "1m": {
        #             timestamp: candle
        #         },
        #         "5m": {...},
        #         "15m": {...},
        #     }
        # }

        self._candles: dict[
            str,
            dict[
                str,
                dict[
                    int,
                    dict[str, Any],
                ],
            ],
        ] = {}

        # Angel One can provide cumulative
        # traded volume. We store the previous
        # value so we can calculate tick volume.

        self._last_volume: dict[
            str,
            float,
        ] = {}

        self._lock = Lock()

    # --------------------------------------------------
    # TIME BUCKET
    # --------------------------------------------------

    @staticmethod
    def _bucket(
        timestamp: float,
        seconds: int,
    ) -> int:

        value = int(timestamp)

        return (
            value
            // seconds
            * seconds
        )

    # --------------------------------------------------
    # VOLUME CALCULATION
    # --------------------------------------------------

    def _volume_delta(
        self,
        symbol: str,
        cumulative_volume: Optional[float],
    ) -> float:

        if cumulative_volume is None:
            return 0.0

        try:
            current = max(
                0.0,
                float(cumulative_volume),
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        previous = self._last_volume.get(
            symbol
        )

        self._last_volume[symbol] = (
            current
        )

        # First tick has no previous volume
        # for comparison.

        if previous is None:
            return 0.0

        delta = current - previous

        # Cumulative volume may reset at
        # the beginning of a new session.

        if delta < 0:
            return 0.0

        return delta

    # --------------------------------------------------
    # UPDATE A CANDLE
    # --------------------------------------------------

    def _update(
        self,
        *,
        symbol: str,
        timeframe: str,
        bucket: int,
        price: float,
        volume_delta: float,
    ) -> None:

        symbol_data = (
            self._candles.setdefault(
                symbol,
                {},
            )
        )

        timeframe_data = (
            symbol_data.setdefault(
                timeframe,
                {},
            )
        )

        candle = timeframe_data.get(
            bucket
        )

        # New candle.

        if candle is None:

            candle = {
                "time": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume_delta,
            }

            timeframe_data[
                bucket
            ] = candle

        # Existing candle.

        else:

            candle["high"] = max(
                float(candle["high"]),
                price,
            )

            candle["low"] = min(
                float(candle["low"]),
                price,
            )

            candle["close"] = price

            candle["volume"] = (
                float(candle["volume"])
                + volume_delta
            )

        # Prevent memory from growing forever.

        while (
            len(timeframe_data)
            > self.max_candles
        ):

            oldest = min(
                timeframe_data
            )

            del timeframe_data[
                oldest
            ]

    # --------------------------------------------------
    # INGEST LIVE MARKET TICK
    # --------------------------------------------------

    def ingest(
        self,
        *,
        symbol: str,
        price: float,
        timestamp: Optional[float] = None,
        cumulative_volume: Optional[
            float
        ] = None,
    ) -> None:

        symbol = (
            str(symbol)
            .strip()
            .upper()
        )

        if not symbol:
            return

        try:
            price = float(price)

        except (
            TypeError,
            ValueError,
        ):
            return

        if price <= 0:
            return

        # If Angel One timestamp is unavailable,
        # use the current UTC timestamp.

        if timestamp is None:

            timestamp = (
                datetime.now(
                    timezone.utc
                ).timestamp()
            )

        try:
            timestamp = float(timestamp)

        except (
            TypeError,
            ValueError,
        ):

            timestamp = (
                datetime.now(
                    timezone.utc
                ).timestamp()
            )

        with self._lock:

            volume_delta = (
                self._volume_delta(
                    symbol,
                    cumulative_volume,
                )
            )

            # ------------------------------------------
            # 1 MINUTE
            # ------------------------------------------

            self._update(
                symbol=symbol,
                timeframe="1m",
                bucket=self._bucket(
                    timestamp,
                    60,
                ),
                price=price,
                volume_delta=(
                    volume_delta
                ),
            )

            # ------------------------------------------
            # 5 MINUTES
            # ------------------------------------------

            self._update(
                symbol=symbol,
                timeframe="5m",
                bucket=self._bucket(
                    timestamp,
                    300,
                ),
                price=price,
                volume_delta=(
                    volume_delta
                ),
            )

            # ------------------------------------------
            # 15 MINUTES
            # ------------------------------------------

            self._update(
                symbol=symbol,
                timeframe="15m",
                bucket=self._bucket(
                    timestamp,
                    900,
                ),
                price=price,
                volume_delta=(
                    volume_delta
                ),
            )

    # --------------------------------------------------
    # GET CANDLES
    # --------------------------------------------------

    def candles(
        self,
        symbol: str,
        timeframe: str,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:

        symbol = (
            str(symbol)
            .strip()
            .upper()
        )

        if timeframe not in {
            "1m",
            "5m",
            "15m",
        }:

            raise ValueError(
                "Timeframe must be "
                "1m, 5m, or 15m"
            )

        with self._lock:

            timeframe_data = (
                self._candles
                .get(
                    symbol,
                    {},
                )
                .get(
                    timeframe,
                    {},
                )
            )

            result = [
                dict(candle)
                for _, candle
                in sorted(
                    timeframe_data.items()
                )
            ]

        if limit is not None:

            result = result[
                -limit:
            ]

        return result

    # --------------------------------------------------
    # GET LATEST CANDLE
    # --------------------------------------------------

    def latest(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[dict[str, Any]]:

        candles = self.candles(
            symbol,
            timeframe,
            limit=1,
        )

        if not candles:
            return None

        return candles[-1]

    # --------------------------------------------------
    # GET ALL TIMEFRAMES
    # --------------------------------------------------

    def snapshot(
        self,
        symbol: str,
    ) -> dict[str, Any]:

        normalized_symbol = (
            str(symbol)
            .strip()
            .upper()
        )

        return {
            "symbol": normalized_symbol,

            "1m": self.candles(
                normalized_symbol,
                "1m",
            ),

            "5m": self.candles(
                normalized_symbol,
                "5m",
            ),

            "15m": self.candles(
                normalized_symbol,
                "15m",
            ),
        }
         # --------------------------------------------------
    # LOAD HISTORICAL CANDLES
    # --------------------------------------------------

    def seed(
        self,
        *,
        symbol: str,
        timeframe: str,
        candles: list[dict[str, Any]],
    ) -> int:

        symbol = (
            str(symbol)
            .strip()
            .upper()
        )

        if timeframe not in {
            "1m",
            "5m",
            "15m",
        }:
            raise ValueError(
                "Timeframe must be "
                "1m, 5m, or 15m"
            )

        loaded = 0

        with self._lock:

            symbol_data = (
                self._candles.setdefault(
                    symbol,
                    {},
                )
            )

            timeframe_data = (
                symbol_data.setdefault(
                    timeframe,
                    {},
                )
            )

            for source in candles:

                try:
                    raw_time = source.get(
                        "time"
                    )

                    if isinstance(
                        raw_time,
                        datetime,
                    ):
                        timestamp = int(
                            raw_time.timestamp()
                        )

                    elif isinstance(
                        raw_time,
                        str,
                    ):
                        timestamp = int(
                            datetime.fromisoformat(
                                raw_time
                            ).timestamp()
                        )

                    else:
                        timestamp = int(
                            float(raw_time)
                        )

                        if (
                            timestamp
                            > 10_000_000_000
                        ):
                            timestamp //= 1000

                    open_price = float(
                        source["open"]
                    )

                    high = float(
                        source["high"]
                    )

                    low = float(
                        source["low"]
                    )

                    close = float(
                        source["close"]
                    )

                    volume = float(
                        source.get(
                            "volume",
                            0.0,
                        )
                        or 0.0
                    )

                except (
                    TypeError,
                    ValueError,
                    KeyError,
                ):
                    continue

                bucket_seconds = {
                    "1m": 60,
                    "5m": 300,
                    "15m": 900,
                }[timeframe]

                bucket = self._bucket(
                    timestamp,
                    bucket_seconds,
                )

                timeframe_data[
                    bucket
                ] = {
                    "time": bucket,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }

                loaded += 1

            # Keep only the newest candles.

            if (
                len(timeframe_data)
                > self.max_candles
            ):

                buckets = sorted(
                    timeframe_data
                )

                remove_count = (
                    len(timeframe_data)
                    - self.max_candles
                )

                for bucket in buckets[
                    :remove_count
                ]:
                    del timeframe_data[
                        bucket
                    ]

        return loaded
    # --------------------------------------------------
    # SYMBOL COUNT
    # --------------------------------------------------

    def symbols(
        self,
    ) -> list[str]:

        with self._lock:

            return sorted(
                self._candles.keys()
            )