import asyncio
from dataclasses import dataclass
from typing import Any, Iterable

from .live_candles import LiveCandleEngine


@dataclass
class WarmupResult:
    symbols: int
    requests: int
    successful_requests: int
    failed_requests: int
    candles_loaded: int


async def warm_live_candles(
    *,
    market: Any,
    engine: LiveCandleEngine,
    instruments: Iterable[Any],
    concurrency: int = 3,
) -> WarmupResult:
    """
    Seed the live candle engine with historical
    Angel One candles.

    This allows indicators/scanners to work
    immediately instead of waiting for enough
    live candles to accumulate.
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

    semaphore = asyncio.Semaphore(
        max(
            1,
            concurrency,
        )
    )

    requests = 0
    successful_requests = 0
    failed_requests = 0
    candles_loaded = 0

    counter_lock = asyncio.Lock()

    # Enough history for indicators such as:
    # EMA21, MACD26, RSI14, ATR14, etc.
    #
    # We deliberately avoid requesting
    # 30 days for every timeframe.

    timeframe_days = {
        "1m": 2,
        "5m": 5,
        "15m": 10,
    }

    async def load_timeframe(
        item: Any,
        timeframe: str,
    ) -> None:

        nonlocal requests
        nonlocal successful_requests
        nonlocal failed_requests
        nonlocal candles_loaded

        async with semaphore:

            async with counter_lock:
                requests += 1

            try:

                candles = (
                    await market
                    .historical_candles(
                        item.symbol,
                        timeframe,
                        item.token,
                        days=(
                            timeframe_days[
                                timeframe
                            ]
                        ),
                    )
                )

                # We do not need unlimited
                # historical data in memory.

                candles = candles[-200:]

                loaded = engine.seed(
                    symbol=item.symbol,
                    timeframe=timeframe,
                    candles=candles,
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
                    timeframe,
                    exc,
                )

    tasks = []

    for item in items:

        for timeframe in (
            "1m",
            "5m",
            "15m",
        ):

            tasks.append(
                load_timeframe(
                    item,
                    timeframe,
                )
            )

    if tasks:

        await asyncio.gather(
            *tasks
        )

    return WarmupResult(
        symbols=len(items),
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