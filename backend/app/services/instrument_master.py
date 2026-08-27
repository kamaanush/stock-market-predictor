from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Instrument


SCRIP_MASTER_URL = (
    "https://margincalculator.angelone.in/"
    "OpenAPI_File/files/"
    "OpenAPIScripMaster.json"
)


async def refresh_instrument_master(
    session: AsyncSession,
) -> dict[str, Any]:
    """
    Download the latest Angel One scrip master
    and replace the local NSE equity/index
    instrument catalogue in one transaction.

    Watchlist/scan-universe rows are stored in
    a different table and are not deleted.
    """

    async with httpx.AsyncClient(
        timeout=60.0
    ) as client:

        response = await client.get(
            SCRIP_MASTER_URL
        )

        response.raise_for_status()

        records = response.json()


    instruments: list[
        Instrument
    ] = []

    seen_symbols: set[
        str
    ] = set()

    seen_tokens: set[
        str
    ] = set()


    for row in records:

        exchange = str(
            row.get(
                "exch_seg",
                "",
            )
        ).strip().upper()

        raw_symbol = str(
            row.get(
                "symbol",
                "",
            )
        ).strip().upper()

        token = str(
            row.get(
                "token",
                "",
            )
        ).strip()

        instrument_type = str(
            row.get(
                "instrumenttype",
                "",
            )
        ).strip().upper()

        name = str(
            row.get(
                "name",
                "",
            )
            or raw_symbol
        ).strip()


        if (
            exchange != "NSE"
            or not raw_symbol
            or not token
        ):
            continue


        is_equity = (
            instrument_type
            in {
                "",
                "EQ",
            }
            or raw_symbol.endswith(
                "-EQ"
            )
        )

        is_index = (
            instrument_type
            == "AMXIDX"
        )


        if (
            not is_equity
            and not is_index
        ):
            continue


        clean_symbol = (
            raw_symbol.removesuffix(
                "-EQ"
            )
        )


        if (
            clean_symbol
            in seen_symbols
        ):
            continue


        if (
            token
            in seen_tokens
        ):
            continue


        seen_symbols.add(
            clean_symbol
        )

        seen_tokens.add(
            token
        )


        instruments.append(
            Instrument(
                exchange="NSE",

                symbol=(
                    clean_symbol
                ),

                name=(
                    name
                    or clean_symbol
                ),

                token=token,

                kind=(
                    "INDEX"
                    if is_index
                    else "EQUITY"
                ),
            )
        )


    if not instruments:
        raise RuntimeError(
            "Instrument master returned "
            "no usable NSE instruments"
        )


    # Everything happens inside the current
    # database transaction. Existing readers
    # continue using the previous committed
    # catalogue until this transaction commits.

    await session.execute(
        delete(
            Instrument
        )
    )

    session.add_all(
        instruments
    )

    await session.commit()


    return {
        "imported":
            len(instruments),

        "refreshed_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }
