import asyncio

from fastapi import (
    APIRouter,
    Request,
)

from .services.full_market_momentum import (
    FULL_MARKET_SCANNER,
)


router = APIRouter()


@router.get(
    "/api/v2/market-scanner"
)
async def market_scanner(
    request: Request,
):
    """
    IMPORTANT:
    Never make the browser wait for the
    full NSE scanner initialization.

    Start it in the background and immediately
    return the latest snapshot.
    """

    try:
        worker = (
            FULL_MARKET_SCANNER.worker_task
        )

        if (
            worker is None
            or worker.done()
        ):
            asyncio.create_task(
                FULL_MARKET_SCANNER.ensure_started(
                    request.app
                )
            )

        return (
            FULL_MARKET_SCANNER.snapshot()
        )

    except Exception as exc:
        return {
            "status":
                "ERROR",

            "error":
                str(exc),
        }
