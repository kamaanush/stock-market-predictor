from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.market import AngelOneMarketData
from app.models import WatchlistItem

from .candle_history import save_candles
from .market_data_quality import (
    IST,
    nse_session_date,
)


BACKFILL_DAYS = 18


async def main():

    settings = get_settings()

    market = AngelOneMarketData(
        settings
    )

    async with SessionLocal() as session:

        result = await session.execute(
            select(
                WatchlistItem
            )
            .order_by(
                WatchlistItem.symbol
            )
        )

        instruments = list(
            result.scalars()
        )

    # NIFTY benchmark is mandatory.
    if not any(
        item.symbol.strip().upper()
        == "NIFTY 50"
        for item in instruments
    ):
        instruments.append(
            SimpleNamespace(
                symbol="NIFTY 50",
                token="99926000",
            )
        )

    print(
        "Symbols:",
        len(instruments)
    )

    print(
        "Backfill calendar days:",
        BACKFILL_DAYS
    )

    successful = 0
    failed = 0
    total_saved = 0

    for index, item in enumerate(
        instruments,
        start=1,
    ):

        symbol = str(
            item.symbol
        ).strip().upper()

        token = str(
            item.token
        ).strip()

        print()
        print(
            f"[{index}/{len(instruments)}]",
            symbol,
        )

        try:

            candles = (
                await market.long_intraday_history(
                    symbol=symbol,
                    interval="1m",
                    token=token,
                    days=BACKFILL_DAYS,
                )
            )

            # Keep only valid NSE sessions.
            valid = [
                candle
                for candle in candles
                if (
                    nse_session_date(
                        candle["time"]
                    )
                    is not None
                )
            ]

            sessions = sorted(
                {
                    nse_session_date(
                        candle["time"]
                    )
                    for candle in valid
                    if (
                        nse_session_date(
                            candle["time"]
                        )
                        is not None
                    )
                }
            )

            async with SessionLocal() as session:

                saved = await save_candles(
                    session,
                    symbol=symbol,
                    interval="1m",
                    candles=valid,
                )

            successful += 1
            total_saved += saved

            print(
                "candles:",
                len(valid),
                "sessions:",
                len(sessions),
                "new:",
                saved,
            )

            if sessions:

                print(
                    "range:",
                    sessions[0],
                    "->",
                    sessions[-1],
                )

        except Exception as exc:

            failed += 1

            print(
                "❌ FAILED:",
                symbol,
                exc,
            )

    print()
    print(
        "=" * 80
    )

    print(
        "BACKFILL COMPLETE"
    )

    print(
        "Successful:",
        successful
    )

    print(
        "Failed:",
        failed
    )

    print(
        "New candles:",
        total_saved
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
