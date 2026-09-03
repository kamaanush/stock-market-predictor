from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from sqlalchemy import select

from ..database import SessionLocal
from ..models import Instrument


def _num(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    try:
        number = float(value)

        if number != number:
            return default

        return number

    except (TypeError, ValueError):
        return default


def _pct(
    current: Optional[float],
    previous: Optional[float],
) -> Optional[float]:
    if (
        current is None
        or previous is None
        or previous == 0
    ):
        return None

    return (
        (current - previous)
        / previous
        * 100.0
    )


class FullMarketMomentumScanner:
    """
    FULL NSE CASH MARKET SCANNER.

    Uses every NSE EQUITY instrument available
    in the Angel One instrument master.

    This does NOT restrict the universe to:
    - watchlist
    - 228 scanner stocks
    - NIFTY stocks
    - top 400 stocks

    SmartAPI quotes are refreshed continuously
    in rolling batches.
    """

    def __init__(self) -> None:
        self.instruments = []
        self.instrument_by_token = {}

        self.latest = {}

        self.history = defaultdict(
            lambda: deque(
                maxlen=220
            )
        )

        self.started = False
        self.running = False
        self.worker_task = None

        self.initialized_at = None
        self.last_batch_at = None
        self.last_full_cycle_at = None

        self.current_batch = 0
        self.total_batches = 0

        self.successful_batches = 0
        self.failed_batches = 0

        self.last_error = None

        self.batch_size = 50

        # Keep safely around SmartAPI quote
        # rate limits.
        self.batch_delay_seconds = 1.10

        self.lock = asyncio.Lock()

    async def initialize(
        self,
    ) -> None:
        async with self.lock:
            if self.instruments:
                return

            async with SessionLocal() as session:
                result = await session.execute(
                    select(
                        Instrument
                    ).where(
                        Instrument.exchange == "NSE",
                        Instrument.kind == "EQUITY",
                    ).order_by(
                        Instrument.symbol
                    )
                )

                instruments = list(
                    result.scalars()
                )

            output = []

            for item in instruments:
                symbol = str(
                    item.symbol or ""
                ).strip().upper()

                token = str(
                    item.token or ""
                ).strip()

                if (
                    not symbol
                    or not token
                ):
                    continue

                row = {
                    "symbol":
                        symbol,

                    "name":
                        str(
                            item.name
                            or symbol
                        ),

                    "token":
                        token,
                }

                output.append(
                    row
                )

            self.instruments = (
                output
            )

            self.instrument_by_token = {
                item["token"]:
                    item
                for item
                in output
            }

            # Important:
            # create a row immediately for EVERY
            # NSE EQ stock, even before its first
            # live quote reaches us.
            for item in output:
                self.latest[
                    item["symbol"]
                ] = {
                    "symbol":
                        item["symbol"],

                    "name":
                        item["name"],

                    "token":
                        item["token"],

                    "ltp":
                        None,

                    "open":
                        None,

                    "high":
                        None,

                    "low":
                        None,

                    "previous_close":
                        None,

                    "day_change_pct":
                        None,

                    "volume":
                        None,

                    "turnover":
                        None,

                    "change_1m_pct":
                        None,

                    "change_5m_pct":
                        None,

                    "change_15m_pct":
                        None,

                    "momentum_score":
                        None,

                    "momentum_state":
                        "WAITING",

                    "updated_at":
                        None,
                }

            self.total_batches = (
                (
                    len(output)
                    + self.batch_size
                    - 1
                )
                // self.batch_size
            )

            self.initialized_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            print(
                "[FULL MARKET SCANNER]",
                "ALL NSE EQ instruments:",
                len(output),
            )

            print(
                "[FULL MARKET SCANNER]",
                "batches:",
                self.total_batches,
            )

    async def ensure_started(
        self,
        app: Any,
    ) -> None:
        await self.initialize()

        if (
            self.worker_task is None
            or self.worker_task.done()
        ):
            self.running = True

            self.worker_task = (
                asyncio.create_task(
                    self.run_forever(
                        app
                    )
                )
            )

            self.started = True

            print(
                "[FULL MARKET SCANNER]",
                "continuous worker started",
            )

    async def _request_batch(
        self,
        market: Any,
        batch: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        client = getattr(
            market,
            "client",
            None,
        )

        if client is None:
            raise RuntimeError(
                "Angel One SmartAPI client unavailable"
            )

        tokens = [
            item["token"]
            for item in batch
        ]

        response = (
            await asyncio.to_thread(
                client.getMarketData,
                "FULL",
                {
                    "NSE":
                        tokens,
                },
            )
        )

        if not isinstance(
            response,
            dict,
        ):
            raise RuntimeError(
                "Invalid SmartAPI market-data response"
            )

        if not response.get(
            "status",
            False,
        ):
            raise RuntimeError(
                str(
                    response.get(
                        "message",
                        "SmartAPI market-data request failed",
                    )
                )
            )

        data = response.get(
            "data",
            {},
        )

        if not isinstance(
            data,
            dict,
        ):
            return []

        fetched = data.get(
            "fetched",
            [],
        )

        if not isinstance(
            fetched,
            list,
        ):
            return []

        return fetched

    def _history_point(
        self,
        history: Deque[Dict[str, float]],
        target: float,
    ) -> Optional[Dict[str, float]]:
        for point in reversed(
            history
        ):
            if (
                point[
                    "timestamp"
                ]
                <= target
            ):
                return point

        return None

    def _update_quote(
        self,
        quote: Dict[str, Any],
        now_ts: float,
    ) -> None:
        token = str(
            quote.get(
                "symbolToken",
                quote.get(
                    "symboltoken",
                    "",
                ),
            )
        ).strip()

        instrument = (
            self.instrument_by_token.get(
                token
            )
        )

        if instrument is None:
            return

        symbol = instrument[
            "symbol"
        ]

        ltp = _num(
            quote.get(
                "ltp"
            )
        )

        if (
            ltp is None
            or ltp <= 0
        ):
            return

        open_price = _num(
            quote.get(
                "open"
            )
        )

        high = _num(
            quote.get(
                "high"
            )
        )

        low = _num(
            quote.get(
                "low"
            )
        )

        close = _num(
            quote.get(
                "close"
            )
        )

        volume = _num(
            quote.get(
                "tradeVolume",
                quote.get(
                    "tradevolume",
                    quote.get(
                        "volume",
                        0,
                    ),
                ),
            ),
            0.0,
        )

        day_change = _num(
            quote.get(
                "percentChange",
                quote.get(
                    "percentchange"
                ),
            )
        )

        if (
            day_change is None
            and close is not None
            and close != 0
        ):
            day_change = (
                (ltp - close)
                / close
                * 100.0
            )

        history = self.history[
            symbol
        ]

        if (
            not history
            or (
                now_ts
                - history[-1][
                    "timestamp"
                ]
            ) >= 5
        ):
            history.append(
                {
                    "timestamp":
                        now_ts,

                    "ltp":
                        ltp,

                    "volume":
                        (
                            volume
                            or 0.0
                        ),
                }
            )

        p1 = self._history_point(
            history,
            now_ts - 60,
        )

        p5 = self._history_point(
            history,
            now_ts - 300,
        )

        p15 = self._history_point(
            history,
            now_ts - 900,
        )

        change_1m = _pct(
            ltp,
            (
                p1["ltp"]
                if p1
                else None
            ),
        )

        change_5m = _pct(
            ltp,
            (
                p5["ltp"]
                if p5
                else None
            ),
        )

        change_15m = _pct(
            ltp,
            (
                p15["ltp"]
                if p15
                else None
            ),
        )

        score = 0.0

        if change_1m is not None:
            score += (
                change_1m
                * 32
            )

        if change_5m is not None:
            score += (
                change_5m
                * 22
            )

        if change_15m is not None:
            score += (
                change_15m
                * 10
            )

        if day_change is not None:
            score += (
                day_change
                * 2.5
            )

        if score >= 3:
            state = (
                "RISING"
            )

        elif score <= -3:
            state = (
                "FALLING"
            )

        else:
            state = (
                "NEUTRAL"
            )

        turnover = (
            ltp
            * (
                volume
                or 0.0
            )
        )

        self.latest[
            symbol
        ] = {
            "symbol":
                symbol,

            "name":
                instrument[
                    "name"
                ],

            "token":
                token,

            "ltp":
                round(
                    ltp,
                    2,
                ),

            "open":
                open_price,

            "high":
                high,

            "low":
                low,

            "previous_close":
                close,

            "day_change_pct":
                (
                    round(
                        day_change,
                        3,
                    )
                    if day_change
                    is not None
                    else None
                ),

            "volume":
                volume,

            "turnover":
                turnover,

            "change_1m_pct":
                (
                    round(
                        change_1m,
                        3,
                    )
                    if change_1m
                    is not None
                    else None
                ),

            "change_5m_pct":
                (
                    round(
                        change_5m,
                        3,
                    )
                    if change_5m
                    is not None
                    else None
                ),

            "change_15m_pct":
                (
                    round(
                        change_15m,
                        3,
                    )
                    if change_15m
                    is not None
                    else None
                ),

            "momentum_score":
                round(
                    score,
                    2,
                ),

            "momentum_state":
                state,

            "updated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        }

    def _write_snapshot_cache(
        self,
    ) -> None:
        try:
            cache_dir = (
                Path(__file__)
                .resolve()
                .parents[2]
                / "logs"
            )

            cache_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            target = (
                cache_dir
                / "full_market_scanner.json"
            )

            temp = (
                cache_dir
                / "full_market_scanner.tmp"
            )

            payload = (
                self.snapshot()
            )

            temp.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                )
            )

            temp.replace(
                target
            )

        except Exception as exc:
            print(
                "[FULL MARKET SCANNER] cache write failed:",
                exc,
            )

    async def run_forever(
        self,
        app: Any,
    ) -> None:
        while self.running:
            try:
                market = getattr(
                    app.state,
                    "market",
                    None,
                )

                if market is None:
                    raise RuntimeError(
                        "Market client unavailable"
                    )

                instruments = (
                    self.instruments
                )

                batches = [
                    instruments[
                        start:
                        start
                        + self.batch_size
                    ]
                    for start
                    in range(
                        0,
                        len(
                            instruments
                        ),
                        self.batch_size,
                    )
                ]

                for index, batch in enumerate(
                    batches,
                    start=1,
                ):
                    self.current_batch = (
                        index
                    )

                    try:
                        quotes = (
                            await self._request_batch(
                                market,
                                batch,
                            )
                        )

                        now_ts = (
                            time.time()
                        )

                        for quote in quotes:
                            if isinstance(
                                quote,
                                dict,
                            ):
                                self._update_quote(
                                    quote,
                                    now_ts,
                                )

                        self.successful_batches += 1

                        self.last_batch_at = (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        )

                        print(
                            "[FULL MARKET SCANNER]",
                            f"{index}/{len(batches)}",
                            "quotes:",
                            len(quotes),
                        )

                        # Persist frequently so the UI can
                        # read scanner data without another
                        # SmartAPI request.
                        if (
                            index == 1
                            or index % 3 == 0
                        ):
                            self._write_snapshot_cache()

                    except Exception as exc:
                        self.failed_batches += 1

                        self.last_error = (
                            str(exc)
                        )

                        print(
                            "[FULL MARKET SCANNER]",
                            f"batch {index}/{len(batches)} FAILED:",
                            exc,
                        )

                    await asyncio.sleep(
                        self.batch_delay_seconds
                    )

                self.last_full_cycle_at = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

                print(
                    "[FULL MARKET SCANNER]",
                    "FULL NSE cycle complete",
                )

                # Immediately begin another
                # market-wide cycle.
                await asyncio.sleep(
                    1.0
                )

            except asyncio.CancelledError:
                raise

            except Exception as exc:
                self.last_error = (
                    str(exc)
                )

                print(
                    "[FULL MARKET SCANNER] worker error:",
                    exc,
                )

                await asyncio.sleep(
                    3
                )

    def snapshot(
        self,
    ) -> Dict[str, Any]:
        rows = list(
            self.latest.values()
        )

        quoted = [
            row
            for row in rows
            if row.get(
                "ltp"
            )
            is not None
        ]

        waiting = (
            len(rows)
            - len(quoted)
        )

        rising = sorted(
            [
                row
                for row in quoted
                if row.get(
                    "momentum_state"
                ) == "RISING"
            ],
            key=lambda row:
                row.get(
                    "momentum_score",
                    0,
                )
                or 0,
            reverse=True,
        )

        falling = sorted(
            [
                row
                for row in quoted
                if row.get(
                    "momentum_state"
                ) == "FALLING"
            ],
            key=lambda row:
                row.get(
                    "momentum_score",
                    0,
                )
                or 0,
        )

        gainers = sorted(
            quoted,
            key=lambda row:
                row.get(
                    "day_change_pct"
                )
                if row.get(
                    "day_change_pct"
                )
                is not None
                else -999999,
            reverse=True,
        )

        losers = sorted(
            quoted,
            key=lambda row:
                row.get(
                    "day_change_pct"
                )
                if row.get(
                    "day_change_pct"
                )
                is not None
                else 999999,
        )

        volume = sorted(
            quoted,
            key=lambda row:
                row.get(
                    "volume",
                    0,
                )
                or 0,
            reverse=True,
        )

        all_stocks = sorted(
            rows,
            key=lambda row:
                row.get(
                    "symbol",
                    "",
                )
        )

        progress = 0.0

        if self.total_batches:
            progress = (
                self.current_batch
                / self.total_batches
                * 100.0
            )

        return {
            "status":
                (
                    "SCANNING"
                    if self.started
                    else "STARTING"
                ),

            "source":
                "ANGEL_ONE_SMARTAPI",

            "market":
                "NSE_CASH_EQUITY",

            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            # THE IMPORTANT NUMBER:
            # ALL NSE EQ stocks.
            "total_nse_equities":
                len(
                    self.instruments
                ),

            "quoted_count":
                len(
                    quoted
                ),

            "waiting_count":
                waiting,

            "scan_progress_pct":
                round(
                    progress,
                    1,
                ),

            "current_batch":
                self.current_batch,

            "total_batches":
                self.total_batches,

            "last_batch_at":
                self.last_batch_at,

            "last_full_cycle_at":
                self.last_full_cycle_at,

            "last_error":
                self.last_error,

            # ALL STOCKS, not top 50.
            "all_stocks":
                all_stocks,

            "rising":
                rising,

            "falling":
                falling,

            "gainers":
                gainers,

            "losers":
                losers,

            "volume_activity":
                volume,
        }


FULL_MARKET_SCANNER = (
    FullMarketMomentumScanner()
)
