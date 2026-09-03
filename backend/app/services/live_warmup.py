import asyncio
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Iterable

from ..database import SessionLocal
from .candle_history import save_candles
from .live_candles import LiveCandleEngine


@dataclass
class WarmupResult:
    symbols: int
    requests: int
    successful_requests: int
    failed_requests: int
    candles_loaded: int


def _epoch_seconds(
    value: Any,
) -> int:
    if isinstance(
        value,
        datetime,
    ):
        return int(
            value.timestamp()
        )

    if isinstance(
        value,
        str,
    ):
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        return int(
            parsed.timestamp()
        )

    timestamp = float(
        value
    )

    if timestamp > 10_000_000_000:
        timestamp /= 1000.0

    return int(
        timestamp
    )


def _resample(
    candles: list[
        dict[str, Any]
    ],
    seconds: int,
) -> list[
    dict[str, Any]
]:
    """
    Build higher-timeframe candles from 1m data.

    This avoids extra Angel One historical
    API requests for 5m and 15m candles.
    """

    buckets: dict[
        int,
        dict[str, Any],
    ] = {}

    for candle in candles:
        try:
            timestamp = (
                _epoch_seconds(
                    candle["time"]
                )
            )

            bucket = (
                timestamp
                // seconds
                * seconds
            )

            open_price = float(
                candle["open"]
            )

            high = float(
                candle["high"]
            )

            low = float(
                candle["low"]
            )

            close = float(
                candle["close"]
            )

            volume = float(
                candle.get(
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

        existing = buckets.get(
            bucket
        )

        if existing is None:
            buckets[bucket] = {
                "time": bucket,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }

        else:
            existing[
                "high"
            ] = max(
                float(
                    existing["high"]
                ),
                high,
            )

            existing[
                "low"
            ] = min(
                float(
                    existing["low"]
                ),
                low,
            )

            existing[
                "close"
            ] = close

            existing[
                "volume"
            ] = (
                float(
                    existing["volume"]
                )
                + volume
            )

    return [
        buckets[key]
        for key in sorted(
            buckets
        )
    ]


async def warm_live_candles(
    *,
    market: Any,
    engine: LiveCandleEngine,
    instruments: Iterable[Any],
    concurrency: int = 3,
) -> WarmupResult:
    """
    Warm the live scanner from Angel One
    historical 1-minute candles.

    Only one Angel historical request is made
    per symbol.

    5m and 15m candles are generated locally.

    1m candles are persisted for replay mode.
    """

    items = [
        item
        for item in instruments
        if getattr(
            item,
            "token",
            None,
        )
    ]

    # ---------------------------------------------
    # NIFTY BENCHMARK
    # ---------------------------------------------

    if not any(
        str(
            item.symbol
        ).strip().upper()
        == "NIFTY 50"
        for item in items
    ):
        items.append(
            SimpleNamespace(
                symbol="NIFTY 50",
                token="99926000",
            )
        )

    semaphore = (
        asyncio.Semaphore(
            max(
                1,
                concurrency,
            )
        )
    )

    # Angel One historical API needs
    # controlled request pacing.
    historical_lock = (
        asyncio.Lock()
    )

    persistence_lock = (
        asyncio.Lock()
    )

    counter_lock = (
        asyncio.Lock()
    )

    requests = 0
    successful_requests = 0
    failed_requests = 0
    candles_loaded = 0

    async def load_symbol(
        item: Any,
    ) -> None:
        nonlocal requests
        nonlocal successful_requests
        nonlocal failed_requests
        nonlocal candles_loaded

        async with semaphore:
            async with counter_lock:
                requests += 1

            try:
                # -----------------------------------------
                # ONE ANGEL REQUEST PER SYMBOL
                # -----------------------------------------

                async with historical_lock:
                    one_minute = (
                        await market
                        .historical_candles(
                            item.symbol,
                            "1m",
                            item.token,
                            days=7,
                        )
                    )

                    # Prevent historical API bursts.
                    await asyncio.sleep(
                        0.45
                    )

                # Keep several trading sessions
                # permanently for time-normalized
                # volume analysis.
                history_1m = (
                    one_minute[
                        -3000:
                    ]
                )

                # Live indicator memory does not
                # need all historical sessions.
                live_1m = (
                    history_1m[
                        -500:
                    ]
                )

                if not live_1m:
                    raise RuntimeError(
                        "No historical candles"
                    )

                five_minute = (
                    _resample(
                        live_1m,
                        300,
                    )
                )

                fifteen_minute = (
                    _resample(
                        live_1m,
                        900,
                    )
                )

                loaded = 0

                loaded += engine.seed(
                    symbol=item.symbol,
                    timeframe="1m",
                    candles=live_1m,
                )

                loaded += engine.seed(
                    symbol=item.symbol,
                    timeframe="5m",
                    candles=five_minute,
                )

                loaded += engine.seed(
                    symbol=item.symbol,
                    timeframe="15m",
                    candles=fifteen_minute,
                )

                # -----------------------------------------
                # PERMANENT REPLAY HISTORY
                # -----------------------------------------

                async with (
                    persistence_lock
                ):
                    async with (
                        SessionLocal()
                        as db_session
                    ):
                        await save_candles(
                            db_session,
                            symbol=item.symbol,
                            interval="1m",
                            candles=(
                                history_1m
                            ),
                        )

                async with counter_lock:
                    successful_requests += 1
                    candles_loaded += loaded

            except Exception as exc:
                async with counter_lock:
                    failed_requests += 1

                print(
                    "LIVE WARMUP FAILED:",
                    item.symbol,
                    exc,
                )

    tasks = [
        load_symbol(
            item
        )
        for item in items
    ]

    if tasks:
        await asyncio.gather(
            *tasks
        )

    result = WarmupResult(
        symbols=len(
            items
        ),
        requests=requests,
        successful_requests=(
            successful_requests
        ),
        failed_requests=(
            failed_requests
        ),
        candles_loaded=(
            candles_loaded
        ),
    )

    print(
        "LIVE WARMUP COMPLETE:",
        result,
    )

    return result
