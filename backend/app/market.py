import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import pyotp

from .config import Settings


IST = timezone(
    timedelta(
        hours=5,
        minutes=30,
    )
)


INTERVAL_MAP = {
    "1m": "ONE_MINUTE",
    "5m": "FIVE_MINUTE",
    "15m": "FIFTEEN_MINUTE",
}


@dataclass
class Quote:
    symbol: str
    last_price: float
    open: float
    high: float
    low: float
    previous_close: float
    updated_at: datetime

    @property
    def change_percent(self) -> float:
        if self.previous_close == 0:
            return 0.0

        return round(
            (
                (
                    self.last_price
                    - self.previous_close
                )
                / self.previous_close
            )
            * 100,
            2,
        )


class FifteenSecondAggregator:
    """
    Keeps today's in-process 15-second candles.

    Historical 15-second data is not provided.
    """

    def __init__(self) -> None:
        self.candles: dict[
            str,
            dict[
                int,
                dict[str, float],
            ],
        ] = {}

    def ingest(
        self,
        symbol: str,
        price: float,
        timestamp: Optional[
            datetime
        ] = None,
    ) -> dict[str, float]:

        now = (
            timestamp
            or datetime.now(IST)
        ).astimezone(IST)

        bucket = (
            int(
                now.timestamp()
            )
            // 15
            * 15
        )

        series = (
            self.candles
            .setdefault(
                symbol,
                {},
            )
        )

        candle = series.get(
            bucket
        )

        if candle is None:
            candle = {
                "time": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 0.0,
            }

            series[bucket] = (
                candle
            )

        else:
            candle["high"] = max(
                candle["high"],
                price,
            )

            candle["low"] = min(
                candle["low"],
                price,
            )

            candle["close"] = (
                price
            )

        return candle

    def series(
        self,
        symbol: str,
    ) -> list[
        dict[str, float]
    ]:
        return list(
            self.candles.get(
                symbol,
                {},
            ).values()
        )


class DemoMarketData:
    """
    Safe local fallback when SmartAPI
    credentials are not configured.

    Different synthetic behaviour is generated
    for 1m, 5m and 15m so multi-timeframe logic
    can be tested.
    """

    base_prices = {
        "RELIANCE": 1422.8,
        "TCS": 3310.5,
        "INFY": 1512.4,
        "HDFCBANK": 1917.6,
        "NIFTY 50": 24801.3,
    }

    def __init__(
        self,
    ) -> None:
        self.aggregator = (
            FifteenSecondAggregator()
        )

    async def quote(
        self,
        symbol: str,
        token: str = "",
    ) -> Quote:

        now = datetime.now(
            IST
        )

        base = (
            self.base_prices.get(
                symbol.upper(),
                1000.0,
            )
        )

        phase = (
            now.timestamp()
            / 20
            + sum(
                ord(char)
                for char
                in symbol
            )
        )

        last = round(
            base
            * (
                1
                + math.sin(
                    phase
                )
                * 0.0015
            ),
            2,
        )

        quote = Quote(
            symbol=symbol,

            last_price=last,

            open=round(
                base * 0.998,
                2,
            ),

            high=round(
                base * 1.005,
                2,
            ),

            low=round(
                base * 0.995,
                2,
            ),

            previous_close=base,

            updated_at=now,
        )

        self.aggregator.ingest(
            symbol,
            quote.last_price,
            now,
        )

        return quote

    async def candles(
        self,
        symbol: str,
        interval: str,
        token: str = "",
    ) -> list[
        dict[str, float]
    ]:

        if interval == "15s":
            await self.quote(
                symbol,
                token,
            )

            return (
                self.aggregator
                .series(
                    symbol
                )
            )

        if interval not in {
            "1m",
            "5m",
            "15m",
        }:
            raise ValueError(
                "Unsupported interval"
            )

        seconds = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
        }[interval]

        timeframe_factor = {
            "1m": 1.0,
            "5m": 1.6,
            "15m": 2.3,
        }[interval]

        wave_speed = {
            "1m": 6.5,
            "5m": 10.0,
            "15m": 15.0,
        }[interval]

        now = datetime.now(
            IST
        )

        base = (
            self.base_prices.get(
                symbol.upper(),
                1000.0,
            )
        )

        symbol_seed = (
            sum(
                ord(char)
                for char
                in symbol.upper()
            )
            % 20
        )

        output: list[
            dict[str, float]
        ] = []

        for index in range(
            120
        ):

            timestamp = (
                now
                - timedelta(
                    seconds=(
                        seconds
                        * (
                            120
                            - index
                        )
                    )
                )
            )

            trend_component = (
                index
                / 120
                * 0.004
                * timeframe_factor
            )

            wave_component = (
                math.sin(
                    (
                        index
                        + symbol_seed
                    )
                    / wave_speed
                )
                * 0.008
                * timeframe_factor
            )

            secondary_wave = (
                math.cos(
                    (
                        index
                        + symbol_seed
                    )
                    / (
                        wave_speed
                        * 0.55
                    )
                )
                * 0.002
            )

            pivot = (
                base
                * (
                    1
                    + trend_component
                    + wave_component
                    + secondary_wave
                )
            )

            open_price = round(
                pivot
                * (
                    1
                    + math.sin(
                        (
                            index
                            + symbol_seed
                        )
                        / timeframe_factor
                    )
                    * 0.001
                ),
                2,
            )

            close = round(
                pivot
                * (
                    1
                    + math.cos(
                        (
                            index
                            + symbol_seed
                        )
                        / timeframe_factor
                    )
                    * 0.0012
                ),
                2,
            )

            wick_factor = (
                0.0015
                * timeframe_factor
            )

            high = round(
                max(
                    open_price,
                    close,
                )
                * (
                    1
                    + wick_factor
                ),
                2,
            )

            low = round(
                min(
                    open_price,
                    close,
                )
                * (
                    1
                    - wick_factor
                ),
                2,
            )

            volume_wave = (
                1
                + abs(
                    math.sin(
                        (
                            index
                            + symbol_seed
                        )
                        / 9
                    )
                )
                * 0.25
            )

            volume = round(
                (
                    10000
                    + index * 120
                )
                * timeframe_factor
                * volume_wave,
                2,
            )

            output.append(
                {
                    "time": int(
                        timestamp.timestamp()
                    ),

                    "open": (
                        open_price
                    ),

                    "high": high,

                    "low": low,

                    "close": close,

                    "volume": volume,
                }
            )

        return output

    async def historical_candles(
        self,
        symbol: str,
        interval: str,
        token: str = "",
        days: int = 30,
    ) -> list[
        dict[str, float]
    ]:
        """
        Demo fallback.

        Days is accepted so the same API can be
        used in demo and SmartAPI modes.

        Demo still returns synthetic candles only.
        """

        return await self.candles(
            symbol,
            interval,
            token,
        )


class AngelOneMarketData:
    """
    Read-only SmartAPI market-data client.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        self.auth_token = ""
        self.refresh_token = ""
        self.feed_token = ""

        from SmartApi import (
            SmartConnect,
        )

        self.settings = settings

        self.client = SmartConnect(
            api_key=(
                settings.smartapi_api_key
            )
        )

        self._login()

        self.aggregator = (
            FifteenSecondAggregator()
        )

    def _login(
        self,
    ) -> None:

        totp = pyotp.TOTP(
            self.settings.smartapi_totp_secret
        ).now()

        response = (
            self.client.generateSession(
                self.settings.smartapi_client_code,
                self.settings.smartapi_pin,
                totp,
            )
        )

        if not response.get("status"):

            message = response.get(
                "message",
                "unknown error",
            )

            raise RuntimeError(
                "SmartAPI login failed: "
                + str(message)
            )

        data = response.get(
            "data",
            {},
        )

        self.auth_token = str(
            data.get(
                "jwtToken",
                "",
            )
        )

        self.refresh_token = str(
            data.get(
                "refreshToken",
                "",
            )
        )

        self.feed_token = str(
            self.client.getfeedToken()
            or ""
        )

        if not self.auth_token:
            raise RuntimeError(
                "SmartAPI login succeeded "
                "but JWT token is missing"
            )

        if not self.feed_token:
            raise RuntimeError(
                "SmartAPI login succeeded "
                "but feed token is missing"
            )

    @staticmethod
    def _is_invalid_token(
        response: dict,
    ) -> bool:
        if response.get("status"):
            return False

        message = str(
            response.get(
                "message",
                "",
            )
        ).lower()

        return (
            "invalid token" in message
            or "token is invalid" in message
            or "token expired" in message
        )

    async def quote(
        self,
        symbol: str,
        token: str,
    ) -> Quote:

        def fetch() -> Quote:

            response = (
                self.client
                .ltpData(
                    "NSE",
                    symbol,
                    token,
                )
            )

            if self._is_invalid_token(
                response
            ):
                print(
                    "[SmartAPI] Quote token invalid "
                    f"for {symbol}. Re-authenticating..."
                )

                self._login()

                response = (
                    self.client
                    .ltpData(
                        "NSE",
                        symbol,
                        token,
                    )
                )

            if not response.get(
                "status"
            ):
                raise RuntimeError(
                    response.get(
                        "message",
                        (
                            "Unable to "
                            "fetch quote"
                        ),
                    )
                )

            data = response[
                "data"
            ]

            price = float(
                data["ltp"]
            )

            return Quote(
                symbol=symbol,

                last_price=price,

                open=float(
                    data.get(
                        "open",
                        price,
                    )
                ),

                high=float(
                    data.get(
                        "high",
                        price,
                    )
                ),

                low=float(
                    data.get(
                        "low",
                        price,
                    )
                ),

                previous_close=float(
                    data.get(
                        "close",
                        price,
                    )
                ),

                updated_at=(
                    datetime.now(
                        IST
                    )
                ),
            )

        quote = (
            await asyncio.to_thread(
                fetch
            )
        )

        self.aggregator.ingest(
            symbol,
            quote.last_price,
            quote.updated_at,
        )

        return quote

    async def candles(
        self,
        symbol: str,
        interval: str,
        token: str,
    ) -> list[
        dict[str, float]
    ]:

        if interval == "15s":

            await self.quote(
                symbol,
                token,
            )

            return (
                self.aggregator
                .series(
                    symbol
                )
            )

        if (
            interval
            not in INTERVAL_MAP
        ):
            raise ValueError(
                "Unsupported interval"
            )

        def fetch() -> list[
            dict[str, float]
        ]:

            now = datetime.now(
                IST
            )

            payload = {
                "exchange": "NSE",

                "symboltoken": token,

                "interval": (
                    INTERVAL_MAP[
                        interval
                    ]
                ),

                "fromdate": (
                    now
                    - timedelta(
                        days=5
                    )
                ).strftime(
                    "%Y-%m-%d %H:%M"
                ),

                "todate": (
                    now.strftime(
                        "%Y-%m-%d %H:%M"
                    )
                ),
            }

            response = (
                self.client
                .getCandleData(
                    payload
                )
            )

            if self._is_invalid_token(
                response
            ):
                print(
                    "[SmartAPI] Candle token invalid "
                    f"for {symbol}. Re-authenticating..."
                )

                self._login()

                response = (
                    self.client
                    .getCandleData(
                        payload
                    )
                )

            if not response.get(
                "status"
            ):
                raise RuntimeError(
                    response.get(
                        "message",
                        (
                            "Unable to "
                            "fetch candles"
                        ),
                    )
                )

            return (
                self._parse_candles(
                    response
                )
            )

        return await asyncio.to_thread(
            fetch
        )

    async def historical_candles(
        self,
        symbol: str,
        interval: str,
        token: str,
        days: int = 30,
    ) -> list[
        dict[str, float]
    ]:

        if (
            interval
            not in INTERVAL_MAP
        ):
            raise ValueError(
                "Unsupported interval"
            )

        if days < 1:
            raise ValueError(
                "Days must be at least 1"
            )

        def fetch() -> list[
            dict[str, float]
        ]:

            now = datetime.now(
                IST
            )

            payload = {
                "exchange": "NSE",

                "symboltoken": token,

                "interval": (
                    INTERVAL_MAP[
                        interval
                    ]
                ),

                "fromdate": (
                    now
                    - timedelta(
                        days=days
                    )
                ).strftime(
                    "%Y-%m-%d %H:%M"
                ),

                "todate": (
                    now.strftime(
                        "%Y-%m-%d %H:%M"
                    )
                ),
            }

            response = (
                self.client
                .getCandleData(
                    payload
                )
            )

            if self._is_invalid_token(
                response
            ):
                print(
                    "[SmartAPI] Historical token invalid "
                    f"for {symbol}. Re-authenticating..."
                )

                self._login()

                response = (
                    self.client
                    .getCandleData(
                        payload
                    )
                )

            if not response.get(
                "status"
            ):
                raise RuntimeError(
                    response.get(
                        "message",
                        (
                            "Unable to fetch "
                            "historical candles"
                        ),
                    )
                )

            return (
                self._parse_candles(
                    response
                )
            )

        return await asyncio.to_thread(
            fetch
        )

    @staticmethod
    def _parse_candles(
        response: dict,
    ) -> list[
        dict[str, float]
    ]:

        output: list[
            dict[str, float]
        ] = []

        for row in response.get(
            "data",
            [],
        ):

            timestamp_text = str(
                row[0]
            )

            timestamp = (
                datetime.fromisoformat(
                    timestamp_text.replace(
                        "Z",
                        "+00:00",
                    )
                )
            )

            output.append(
                {
                    "time": int(
                        timestamp.timestamp()
                    ),

                    "open": float(
                        row[1]
                    ),

                    "high": float(
                        row[2]
                    ),

                    "low": float(
                        row[3]
                    ),

                    "close": float(
                        row[4]
                    ),

                    "volume": float(
                        row[5]
                        or 0
                    ),
                }
            )

        return output


def create_market_data(
    settings: Settings,
) -> Union[
    DemoMarketData,
    AngelOneMarketData,
]:

    if settings.smartapi_ready:
        return AngelOneMarketData(
            settings
        )

    return DemoMarketData()