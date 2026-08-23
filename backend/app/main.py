import asyncio
import csv
import hmac
import io
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from typing import Any, Optional, Union

import httpx
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    delete,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from .config import get_settings
from .database import SessionLocal, get_session, initialize_database
from .market import IST, DemoMarketData, Quote, create_market_data
from .models import (
    Alert,
    AlertEvent,
    ImportBatch,
    Instrument,
    PortfolioHolding,
    WatchlistItem,
)
from .notifications import send_telegram
from .schemas import (
    AlertEventOut,
    AlertInput,
    AlertOut,
    CandleOut,
    HoldingInput,
    HoldingOut,
    InstrumentOut,
    LoginRequest,
    QuoteOut,
    ScannerResultOut,
    ScannerV2Out,
    WatchlistCreate,
    WatchlistOut,
)
from .services.market_scan_service import (
    ScanInstrument,
    market_scan_to_dict,
    run_market_scan,
)
from .services.scanner import scan_symbol
from .services.scanner_v2 import build_scanner_v2_response
from .services.backtester import (
    backtest_to_dict,
    run_backtest,
)
from .services.live_market import LiveMarketTracker
from .services.live_candles import LiveCandleEngine
from .services.live_market import LiveMarketTracker
from .services.live_candles import LiveCandleEngine

from .services.candle_history import (
    latest_candle_time,
    load_candles,
    save_candles,
)

SCRIP_MASTER_URL = (
    "https://margincalculator.angelone.in/"
    "OpenAPI_File/files/OpenAPIScripMaster.json"
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    await initialize_database()
    await seed_demo_instruments()

    app.state.live_market = None

    app.state.live_candles = LiveCandleEngine(
    max_candles=500
     )

    try:
        app.state.market = create_market_data(
            get_settings()
        )
        app.state.market_warning = ""

    except Exception as exc:
        app.state.market = DemoMarketData()
        app.state.market_warning = (
            "SmartAPI connection failed; "
            "using demo market data. "
            f"{exc}"
        )

    # -------------------------------------------------
    # V1.8 LIVE ANGEL ONE MARKET FEED
    # -------------------------------------------------

    market_client = app.state.market

    if (
        hasattr(market_client, "auth_token")
        and hasattr(market_client, "feed_token")
    ):

        try:

            async with SessionLocal() as session:

                watchlist = list(
                    (
                        await session.execute(
                            select(
                                WatchlistItem
                            ).order_by(
                                WatchlistItem.symbol
                            )
                        )
                    ).scalars()
                )

            if watchlist:

                settings = get_settings()

                live_market = LiveMarketTracker(
                    auth_token=(
                        market_client.auth_token
                    ),
                    api_key=(
                        settings.smartapi_api_key
                    ),
                    client_code=(
                        settings.smartapi_client_code
                    ),
                    feed_token=(
                        market_client.feed_token
                    ),
                )

                live_market.configure(
                    [
                        (
                            item.symbol,
                            item.token,
                        )
                        for item in watchlist
                        if item.token
                    ]
                )

                def handle_live_tick(
                    tick: dict[str, Any],
                ) -> None:

                    symbol = tick.get(
                        "symbol"
                    )

                    price = tick.get(
                        "ltp"
                    )

                    if (
                        not symbol
                        or price is None
                    ):
                        return

                    exchange_timestamp = (
                        tick.get(
                            "exchange_timestamp"
                        )
                    )

                    timestamp = None

                    if (
                        exchange_timestamp
                        is not None
                    ):

                        try:
                            timestamp = float(
                                exchange_timestamp
                            )

                            if (
                                timestamp
                                > 10_000_000_000
                            ):
                                timestamp /= 1000.0

                        except (
                            TypeError,
                            ValueError,
                        ):
                            timestamp = None

                    cumulative_volume = (
                        tick.get(
                            "volume"
                        )
                    )

                    app.state.live_candles.ingest(
                        symbol=str(
                            symbol
                        ),
                        price=float(
                            price
                        ),
                        timestamp=timestamp,
                        cumulative_volume=(
                            cumulative_volume
                        ),
                    )

                live_market.add_listener(
                    handle_live_tick
                )

                live_market.start()

                app.state.live_market = (
                    live_market
                )

                print(
                    "V1.8 LIVE MARKET STARTED:",
                    len(watchlist),
                    "stocks",
                )
            else:

                print(
                    "V1.8 LIVE MARKET: "
                    "watchlist is empty"
                )

        except Exception as exc:

            print(
                "V1.8 LIVE MARKET "
                "START FAILED:",
                exc,
            )

    alert_worker = asyncio.create_task(
        alert_worker_loop(app)
    )

    try:
        yield

    finally:

        live_market = getattr(
            app.state,
            "live_market",
            None,
        )

        if live_market is not None:
            live_market.stop()

        alert_worker.cancel()

        with suppress(
            asyncio.CancelledError
        ):
            await alert_worker


async def seed_demo_instruments() -> None:
    """Provide a useful first-run catalogue without requiring a network request."""
    demo_instruments = [
        ("RELIANCE", "Reliance Industries", "2885", "EQUITY"),
        ("TCS", "Tata Consultancy Services", "11536", "EQUITY"),
        ("INFY", "Infosys", "1594", "EQUITY"),
        ("HDFCBANK", "HDFC Bank", "1333", "EQUITY"),
        ("NIFTY 50", "NIFTY 50", "99926000", "INDEX"),
    ]

    async with SessionLocal() as session:
        for symbol, name, token, kind in demo_instruments:
            existing = (
                await session.execute(
                    select(Instrument).where(
                        (Instrument.symbol == symbol)
                        | (Instrument.token == token)
                    )
                )
            ).scalars().first()

            if existing is None:
                session.add(
                    Instrument(
                        exchange="NSE",
                        symbol=symbol,
                        name=name,
                        token=token,
                        kind=kind,
                    )
                )

        await session.commit()


async def alert_worker_loop(app: FastAPI) -> None:
    """Evaluate price alerts periodically while the backend is running."""
    while True:
        try:
            await evaluate_alerts_once(app)
        except Exception:
            pass

        await asyncio.sleep(10)


async def evaluate_alerts_once(app: FastAPI) -> None:
    telegram_messages: list[str] = []

    async with SessionLocal() as session:
        alerts = list(
            (
                await session.execute(
                    select(Alert).where(Alert.active.is_(True))
                )
            ).scalars()
        )

        for alert in alerts:
            try:
                instrument = await resolve_instrument(
                    session,
                    alert.symbol,
                )
                quote = await app.state.market.quote(
                    alert.symbol,
                    instrument.token,
                )
            except Exception:
                continue

            triggered = (
                alert.condition == "ABOVE"
                and quote.last_price >= alert.target_price
            ) or (
                alert.condition == "BELOW"
                and quote.last_price <= alert.target_price
            )

            if not triggered:
                continue

            message = (
                f"{alert.symbol} is {quote.last_price:,.2f}: "
                f"alert {alert.condition.lower()} "
                f"{alert.target_price:,.2f} triggered."
            )

            session.add(
                AlertEvent(
                    alert_id=alert.id,
                    symbol=alert.symbol,
                    message=message,
                    delivery=alert.delivery,
                )
            )

            alert.active = False
            alert.last_triggered_at = datetime.now(IST)

            if alert.delivery in {"TELEGRAM", "BOTH"}:
                telegram_messages.append(message)

        await session.commit()

    for message in telegram_messages:
        try:
            await send_telegram(settings, message)
        except Exception:
            pass

def aggregate_weekly(
    candles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[int, int],
        list[dict[str, Any]],
    ] = {}

    for candle in candles:
        dt = datetime.fromtimestamp(
            candle["time"],
            IST,
        )

        iso_year, iso_week, _ = (
            dt.isocalendar()
        )

        grouped.setdefault(
            (iso_year, iso_week),
            [],
        ).append(candle)

    output: list[
        dict[str, Any]
    ] = []

    for group in grouped.values():
        group = sorted(
            group,
            key=lambda item: item["time"],
        )

        output.append(
            {
                "time": group[0]["time"],
                "open": group[0]["open"],
                "high": max(
                    item["high"]
                    for item in group
                ),
                "low": min(
                    item["low"]
                    for item in group
                ),
                "close": group[-1]["close"],
                "volume": sum(
                    item.get(
                        "volume",
                        0,
                    )
                    for item in group
                ),
            }
        )

    return output


def aggregate_monthly(
    candles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[int, int],
        list[dict[str, Any]],
    ] = {}

    for candle in candles:
        dt = datetime.fromtimestamp(
            candle["time"],
            IST,
        )

        grouped.setdefault(
            (
                dt.year,
                dt.month,
            ),
            [],
        ).append(candle)

    output: list[
        dict[str, Any]
    ] = []

    for group in grouped.values():
        group = sorted(
            group,
            key=lambda item: item["time"],
        )

        output.append(
            {
                "time": group[0]["time"],
                "open": group[0]["open"],
                "high": max(
                    item["high"]
                    for item in group
                ),
                "low": min(
                    item["low"]
                    for item in group
                ),
                "close": group[-1]["close"],
                "volume": sum(
                    item.get(
                        "volume",
                        0,
                    )
                    for item in group
                ),
            }
        )

    return output

app = FastAPI(
    title="NSE Stock Tracker API",
    version="0.2.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    SessionMiddleware,
    secret_key=(
        settings.session_secret
        or "development-only-change-me"
    ),
    same_site="lax",
    https_only=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def market():
    return app.state.market


async def require_owner(request: Request) -> None:
    if request.session.get("owner") is True:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Login required",
    )


def quote_out(quote: Quote) -> QuoteOut:
    return QuoteOut(
        symbol=quote.symbol,
        last_price=quote.last_price,
        open=quote.open,
        high=quote.high,
        low=quote.low,
        previous_close=quote.previous_close,
        change_percent=quote.change_percent,
        updated_at=quote.updated_at,
    )


async def resolve_instrument(
    session: AsyncSession,
    symbol: str,
) -> Union[Instrument, WatchlistItem, PortfolioHolding]:
    normalized_symbol = symbol.upper()

    result = await session.execute(
        select(Instrument).where(
            Instrument.symbol == normalized_symbol
        )
    )
    instrument = result.scalar_one_or_none()

    if instrument:
        return instrument

    result = await session.execute(
        select(WatchlistItem).where(
            WatchlistItem.symbol == normalized_symbol
        )
    )
    item = result.scalar_one_or_none()

    if item:
        return item

    result = await session.execute(
        select(PortfolioHolding).where(
            PortfolioHolding.symbol == normalized_symbol
        )
    )
    holding = result.scalar_one_or_none()

    if holding:
        return holding

    raise HTTPException(
        status_code=404,
        detail=f"Unknown symbol: {symbol}",
    )


@app.get("/api/health")
async def health() -> dict[str, Union[bool, str]]:
    return {
        "status": "ok",
        "market_mode": (
            "demo"
            if isinstance(market(), DemoMarketData)
            else "smartapi"
        ),
        "smartapi_configured": settings.smartapi_ready,
        "market_warning": app.state.market_warning,
    }



@app.get(
    "/api/v2/backtest/{symbol}",
    dependencies=[Depends(require_owner)],
)
async def backtest_symbol(
    symbol: str,
    interval: str = "5m",
    minimum_confidence: int = 60,
    session: AsyncSession = Depends(get_session),
):
    if interval not in {
        "1m",
        "5m",
        "15m",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "Backtest interval must be "
                "1m, 5m, or 15m"
            ),
        )

    symbol_upper = symbol.upper()

    instrument = await resolve_instrument(
        session,
        symbol_upper,
    )

    try:
        candles = await market().candles(
            instrument.symbol,
            interval,
            instrument.token,
        )

        result = run_backtest(
            symbol=instrument.symbol,
            timeframe=interval,
            candles=candles,
            minimum_confidence=minimum_confidence,
            warmup_bars=60,
            max_hold_bars=12,
        )

        return backtest_to_dict(
            result
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Backtest failed for "
                f"{symbol_upper}: {exc}"
            ),
        ) from exc



@app.get(
    "/api/v2/backtest-history/{symbol}",
    dependencies=[Depends(require_owner)],
)
async def backtest_history(
    symbol: str,
    interval: str = "5m",
    days: int = 30,
    minimum_confidence: int = 60,
    session: AsyncSession = Depends(get_session),
):
    if interval not in {
        "1m",
        "5m",
        "15m",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "Backtest interval must be "
                "1m, 5m, or 15m"
            ),
        )

    if days < 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "Days must be at least 1"
            ),
        )

    symbol_upper = symbol.upper()

    instrument = await resolve_instrument(
        session,
        symbol_upper,
    )

    provider = market()

    try:
        candles = await provider.historical_candles(
            instrument.symbol,
            interval,
            instrument.token,
            days,
        )

        result = run_backtest(
            symbol=instrument.symbol,
            timeframe=interval,
            candles=candles,
            minimum_confidence=minimum_confidence,
            warmup_bars=60,
            max_hold_bars=12,
        )

        response = backtest_to_dict(
            result
        )

        response["requested_days"] = days

        response["market_mode"] = (
            "demo"
            if isinstance(
                provider,
                DemoMarketData,
            )
            else "smartapi"
        )

        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Historical backtest failed "
                f"for {symbol_upper}: {exc}"
            ),
        ) from exc


@app.post("/api/auth/login")
async def login(
    payload: LoginRequest,
    request: Request,
) -> dict[str, bool]:
    if not settings.app_password:
        raise HTTPException(
            status_code=503,
            detail="APP_PASSWORD is not configured",
        )

    if not hmac.compare_digest(
        payload.password,
        settings.app_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid password",
        )

    request.session.clear()
    request.session["owner"] = True

    return {"ok": True}


@app.post("/api/auth/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth/me")
async def me(request: Request) -> dict[str, bool]:
    return {
        "authenticated": request.session.get("owner") is True
    }
@app.get(
    "/api/instruments",
    dependencies=[
        Depends(
            require_owner
        )
    ],
)
async def list_instruments(
    page: int = 1,
    page_size: int = 50,
    q: str = "",
    kind: str = "EQUITY",
    session:
        AsyncSession =
        Depends(
            get_session
        ),
) -> dict[str, Any]:

    if page < 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "Page must be "
                "at least 1"
            ),
        )

    if (
        page_size < 1 or
        page_size > 100
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Page size must "
                "be between "
                "1 and 100"
            ),
        )

    normalized_kind = (
        str(kind)
        .strip()
        .upper()
    )

    term = (
        str(q)
        .strip()
        .upper()
    )

    filters = []

    if (
        normalized_kind
        and
        normalized_kind !=
        "ALL"
    ):
        filters.append(
            Instrument.kind
            ==
            normalized_kind
        )

    if term:
        filters.append(
            Instrument.symbol
            .ilike(
                f"%{term}%"
            )
            |
            Instrument.name
            .ilike(
                f"%{term}%"
            )
        )

    count_query = (
        select(
            func.count(
                Instrument.id
            )
        )
    )

    if filters:
        count_query = (
            count_query
            .where(
                *filters
            )
        )

    total = int(
        (
            await session
            .execute(
                count_query
            )
        )
        .scalar_one()
    )

    offset = (
        page - 1
    ) * page_size

    query = (
        select(
            Instrument
        )
        .order_by(
            Instrument.symbol
            .asc()
        )
        .offset(
            offset
        )
        .limit(
            page_size
        )
    )

    if filters:
        query = (
            query.where(
                *filters
            )
        )

    result = (
        await session
        .execute(
            query
        )
    )

    instruments = list(
        result.scalars()
    )

    pages = max(
        1,
        (
            total
            +
            page_size
            -
            1
        )
        //
        page_size,
    )

    return {
        "items": [
            {
                "exchange":
                    item.exchange,

                "symbol":
                    item.symbol,

                "name":
                    item.name,

                "token":
                    item.token,

                "kind":
                    item.kind,
            }
            for item
            in instruments
        ],

        "page":
            page,

        "page_size":
            page_size,

        "total":
            total,

        "pages":
            pages,
    }

@app.get(
    "/api/instruments/search",
    response_model=list[InstrumentOut],
    dependencies=[Depends(require_owner)],
)
async def search_instruments(
    q: str,
    session: AsyncSession = Depends(get_session),
) -> list[Instrument]:
    term = q.strip().upper()

    if len(term) < 1:
        return []

    query = (
        select(Instrument)
        .where(
            Instrument.symbol.ilike(f"%{term}%")
            | Instrument.name.ilike(f"%{term}%")
        )
        .limit(30)
    )

    return list((await session.execute(query)).scalars())


@app.post(
    "/api/instruments/refresh",
    dependencies=[Depends(require_owner)],
)
async def refresh_instruments(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """Fetch the Angel One master and retain NSE EQ + index entries only."""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(SCRIP_MASTER_URL)
        response.raise_for_status()
        records = response.json()

    await session.execute(delete(Instrument))

    instruments: list[Instrument] = []
    seen_symbols: set[str] = set()

    for row in records:
        exchange = str(row.get("exch_seg", ""))
        symbol = str(row.get("symbol", ""))
        token = str(row.get("token", ""))
        instrument_type = str(row.get("instrumenttype", ""))

        if exchange != "NSE" or not symbol or not token:
            continue

        if (
            instrument_type not in {"", "EQ", "AMXIDX"}
            and not symbol.endswith("-EQ")
        ):
            continue

        clean_symbol = symbol.removesuffix("-EQ")

        if clean_symbol in seen_symbols:
            continue

        seen_symbols.add(clean_symbol)

        instruments.append(
            Instrument(
                exchange="NSE",
                symbol=clean_symbol,
                name=str(row.get("name") or clean_symbol),
                token=token,
                kind=(
                    "INDEX"
                    if instrument_type == "AMXIDX"
                    else "EQUITY"
                ),
            )
        )

    session.add_all(instruments)
    await session.commit()

    return {"imported": len(instruments)}


@app.post(
    "/api/watchlist",
    response_model=WatchlistOut,
    dependencies=[
        Depends(
            require_owner
        )
    ],
    status_code=201,
)
async def add_watchlist(
    payload: WatchlistCreate,
    session: AsyncSession = Depends(
        get_session
    ),
) -> WatchlistOut:

    symbol = (
        payload.symbol
        .strip()
        .upper()
    )


    # ==============================================
    # CHECK EXISTING
    # ==============================================

    existing = (
        await session.execute(
            select(
                WatchlistItem
            ).where(
                WatchlistItem.symbol ==
                symbol
            )
        )
    ).scalar_one_or_none()


    if existing is not None:

        # Repair/re-register old database items
        # with the live tracker as well.

        existing_price = 0.0
        existing_change = 0.0

        try:

            quote = (
                await market().quote(
                    existing.symbol,
                    existing.token,
                )
            )

            existing_price = float(
                quote.last_price
            )

            existing_change = float(
                quote.change_percent or
                0.0
            )

        except Exception as exc:

            print(
                "Existing watchlist "
                "quote unavailable:",
                existing.symbol,
                exc,
            )


        live_market = getattr(
            app.state,
            "live_market",
            None,
        )


        if (
            live_market is not None
            and
            existing.token
        ):

            try:

                live_market.add_instrument(
                    symbol=
                        existing.symbol,

                    token=
                        existing.token,

                    last_price=(
                        existing_price
                        if existing_price > 0
                        else None
                    ),
                )

            except Exception as exc:

                print(
                    "Unable to restore "
                    "existing live stock:",
                    existing.symbol,
                    exc,
                )


        raise HTTPException(
            status_code=409,
            detail=(
                "Symbol is already "
                "in the watchlist"
            ),
        )


    # ==============================================
    # SAVE DATABASE ITEM
    # ==============================================

    item = WatchlistItem(
        symbol=symbol,
        name=payload.name,
        token=payload.token,
        kind=payload.kind,
    )


    session.add(
        item
    )

    await session.commit()


    # ==============================================
    # QUOTE
    #
    # IMPORTANT:
    # Failure to get a quote must NOT undo or
    # break a valid Watchlist addition.
    # ==============================================

    last_price = 0.0
    change_percent = 0.0


    try:

        quote = (
            await market().quote(
                item.symbol,
                item.token,
            )
        )

        last_price = float(
            quote.last_price
        )

        change_percent = float(
            quote.change_percent or
            0.0
        )


    except Exception as exc:

        print(
            "Watchlist quote "
            "temporarily unavailable:",
            item.symbol,
            exc,
        )


    # ==============================================
    # ADD TO LIVE MARKET TRACKER
    # ==============================================

    live_market = getattr(
        app.state,
        "live_market",
        None,
    )


    if (
        live_market is not None
        and
        item.token
    ):

        try:

            live_market.add_instrument(
                symbol=
                    item.symbol,

                token=
                    item.token,

                last_price=(
                    last_price
                    if last_price > 0
                    else None
                ),
            )


            print(
                "WATCHLIST LIVE ADDED:",
                item.symbol,
                item.token,
            )


        except Exception as exc:

            print(
                "Unable to add "
                "watchlist stock "
                "to live tracker:",
                item.symbol,
                exc,
            )


    # ==============================================
    # RESPONSE
    # ==============================================

    return WatchlistOut(
        symbol=
            item.symbol,

        name=
            item.name,

        token=
            item.token,

        kind=
            item.kind,

        last_price=
            last_price,

        change_percent=
            change_percent,
    )


@app.delete(
    "/api/watchlist/{symbol}",
    status_code=204,
    dependencies=[
        Depends(
            require_owner
        )
    ],
)
async def remove_watchlist(
    symbol: str,
    session: AsyncSession = Depends(
        get_session
    ),
) -> None:

    normalized_symbol = (
        str(symbol)
        .strip()
        .upper()
    )


    result = await session.execute(
        delete(
            WatchlistItem
        ).where(
            WatchlistItem.symbol ==
            normalized_symbol
        )
    )


    if (
        result.rowcount == 0
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Watchlist symbol "
                "not found"
            ),
        )


    await session.commit()


    # ==========================================
    # REMOVE FROM LIVE MARKET TRACKER
    # ==========================================

    live_tracker = getattr(
        app.state,
        "live_market",
        None,
    )


    if (
        live_tracker
        is not None
    ):

        live_tracker.remove_instrument(
            normalized_symbol
        )


@app.get(
    "/api/stocks/{symbol}/quote",
    response_model=QuoteOut,
    dependencies=[Depends(require_owner)],
)
async def get_quote(
    symbol: str,
    session: AsyncSession = Depends(get_session),
) -> QuoteOut:
    instrument = await resolve_instrument(
        session,
        symbol,
    )

    return quote_out(
        await market().quote(
            instrument.symbol,
            instrument.token,
        )
    )


@app.get(
    "/api/stocks/{symbol}/candles",
    response_model=list[CandleOut],
    dependencies=[Depends(require_owner)],
)
async def get_candles(
    symbol: str,
    interval: str = "5m",
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, float]]:
    if interval not in {
        "15s",
        "1m",
        "5m",
        "15m",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "Interval must be 15s, 1m, 5m, or 15m"
            ),
        )

    instrument = await resolve_instrument(
        session,
        symbol,
    )

    return await market().candles(
        instrument.symbol,
        interval,
        instrument.token,
    )


@app.get(
    "/api/portfolio/holdings",
    response_model=list[HoldingOut],
    dependencies=[Depends(require_owner)],
)
async def get_holdings(
    session: AsyncSession = Depends(get_session),
) -> list[HoldingOut]:
    holdings = list(
        (
            await session.execute(
                select(PortfolioHolding).order_by(
                    PortfolioHolding.symbol
                )
            )
        ).scalars()
    )

    quotes = await asyncio.gather(
        *(
            market().quote(
                item.symbol,
                item.token,
            )
            for item in holdings
        )
    )

    quotes_by_symbol = {
        quote.symbol: quote
        for quote in quotes
    }

    output: list[HoldingOut] = []

    for holding in holdings:
        current = quotes_by_symbol[
            holding.symbol
        ].last_price

        invested = (
            holding.quantity
            * holding.average_price
        )

        market_value = (
            holding.quantity * current
        )

        pnl = market_value - invested

        output.append(
            HoldingOut(
                symbol=holding.symbol,
                name=holding.name,
                token=holding.token,
                quantity=holding.quantity,
                average_price=holding.average_price,
                current_price=current,
                market_value=round(
                    market_value,
                    2,
                ),
                unrealized_pnl=round(
                    pnl,
                    2,
                ),
                unrealized_pnl_percent=round(
                    pnl / invested * 100,
                    2,
                ),
            )
        )

    return output


@app.put(
    "/api/portfolio/holdings",
    response_model=HoldingOut,
    dependencies=[Depends(require_owner)],
)
async def upsert_holding(
    payload: HoldingInput,
    session: AsyncSession = Depends(get_session),
) -> HoldingOut:
    symbol = payload.symbol.upper()

    holding = (
        await session.execute(
            select(PortfolioHolding).where(
                PortfolioHolding.symbol == symbol
            )
        )
    ).scalar_one_or_none()

    if holding is None:
        holding = PortfolioHolding(
            **payload.model_dump(
                exclude={"symbol"}
            ),
            symbol=symbol,
        )
        session.add(holding)
    else:
        for key, value in payload.model_dump(
            exclude={"symbol"}
        ).items():
            setattr(
                holding,
                key,
                value,
            )

    await session.commit()

    current = (
        await market().quote(
            holding.symbol,
            holding.token,
        )
    ).last_price

    invested = (
        holding.quantity
        * holding.average_price
    )

    value = (
        holding.quantity * current
    )

    pnl = value - invested

    return HoldingOut(
        symbol=holding.symbol,
        name=holding.name,
        token=holding.token,
        quantity=holding.quantity,
        average_price=holding.average_price,
        current_price=current,
        market_value=round(
            value,
            2,
        ),
        unrealized_pnl=round(
            pnl,
            2,
        ),
        unrealized_pnl_percent=round(
            pnl / invested * 100,
            2,
        ),
    )


@app.post(
    "/api/portfolio/import",
    dependencies=[Depends(require_owner)],
)
async def import_holdings(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=422,
            detail="Upload a CSV file",
        )

    try:
        rows = list(
            csv.DictReader(
                io.StringIO(
                    (
                        await file.read()
                    ).decode("utf-8-sig")
                )
            )
        )

        required = {
            "symbol",
            "name",
            "quantity",
            "average_price",
        }

        if (
            not rows
            or not required.issubset(rows[0])
        ):
            raise ValueError(
                "CSV headers must include "
                "symbol,name,quantity,average_price; "
                "token is optional"
            )

        for row in rows:
            symbol = (
                row["symbol"]
                .strip()
                .upper()
            )

            holding = (
                await session.execute(
                    select(
                        PortfolioHolding
                    ).where(
                        PortfolioHolding.symbol
                        == symbol
                    )
                )
            ).scalar_one_or_none()

            values = {
                "name": row["name"].strip(),
                "token": row.get(
                    "token",
                    "",
                ).strip(),
                "quantity": float(
                    row["quantity"]
                ),
                "average_price": float(
                    row["average_price"]
                ),
            }

            if (
                values["quantity"] <= 0
                or values["average_price"] <= 0
            ):
                raise ValueError(
                    f"{symbol}: quantity and "
                    "average_price must be positive"
                )

            if holding is None:
                session.add(
                    PortfolioHolding(
                        symbol=symbol,
                        **values,
                    )
                )
            else:
                for key, value in values.items():
                    setattr(
                        holding,
                        key,
                        value,
                    )

        session.add(
            ImportBatch(
                filename=file.filename,
                row_count=len(rows),
            )
        )

        await session.commit()

        return {"imported": len(rows)}

    except (
        UnicodeDecodeError,
        ValueError,
        KeyError,
    ) as exc:
        await session.rollback()

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@app.get(
    "/api/alerts",
    response_model=list[AlertOut],
    dependencies=[Depends(require_owner)],
)
async def get_alerts(
    session: AsyncSession = Depends(get_session),
) -> list[Alert]:
    return list(
        (
            await session.execute(
                select(Alert).order_by(
                    Alert.id.desc()
                )
            )
        ).scalars()
    )


@app.get(
    "/api/alerts/events",
    response_model=list[AlertEventOut],
    dependencies=[Depends(require_owner)],
)
async def get_alert_events(
    after_id: int = 0,
    session: AsyncSession = Depends(get_session),
) -> list[AlertEvent]:
    return list(
        (
            await session.execute(
                select(AlertEvent)
                .where(
                    AlertEvent.id > after_id
                )
                .order_by(
                    AlertEvent.id
                )
            )
        ).scalars()
    )


@app.post(
    "/api/alerts",
    response_model=AlertOut,
    status_code=201,
    dependencies=[Depends(require_owner)],
)
async def create_alert(
    payload: AlertInput,
    session: AsyncSession = Depends(get_session),
) -> Alert:
    data = payload.model_dump()

    data["symbol"] = payload.symbol.upper()

    alert = Alert(**data)

    session.add(alert)
    await session.commit()
    await session.refresh(alert)

    return alert


@app.patch(
    "/api/alerts/{alert_id}",
    response_model=AlertOut,
    dependencies=[Depends(require_owner)],
)
async def toggle_alert(
    alert_id: int,
    active: bool,
    session: AsyncSession = Depends(get_session),
) -> Alert:
    alert = await session.get(
        Alert,
        alert_id,
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found",
        )

    alert.active = active

    await session.commit()
    await session.refresh(alert)

    return alert


@app.delete(
    "/api/alerts/{alert_id}",
    status_code=204,
    dependencies=[Depends(require_owner)],
)
async def delete_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    alert = await session.get(
        Alert,
        alert_id,
    )

    if not alert:
        raise HTTPException(
            status_code=404,
            detail="Alert not found",
        )

    await session.delete(alert)
    await session.commit()

@app.get(
    "/api/scanner/watchlist",
    response_model=list[ScannerResultOut],
    dependencies=[Depends(require_owner)],
)
async def scan_watchlist(
    interval: str = "5m",
    session: AsyncSession = Depends(get_session),
) -> list[ScannerResultOut]:
    """
    V1 watchlist scanner.
    Kept before /api/scanner/{symbol}
    to avoid dynamic route ambiguity.
    """
    if interval not in {
        "1m",
        "5m",
        "15m",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "Scanner interval must be "
                "1m, 5m, or 15m"
            ),
        )

    items = list(
        (
            await session.execute(
                select(WatchlistItem).order_by(
                    WatchlistItem.symbol
                )
            )
        ).scalars()
    )

    results: list[ScannerResultOut] = []

    for item in items:
        try:
            candles = await market().candles(
                item.symbol,
                interval,
                item.token,
            )

            result = scan_symbol(
                symbol=item.symbol,
                candles=candles,
            )

            results.append(
                ScannerResultOut(
                    **result
                )
            )
        except Exception:
            continue

    return sorted(
        results,
        key=lambda item: item.score,
        reverse=True,
    )


@app.get(
    "/api/scanner/{symbol}",
    response_model=ScannerResultOut,
    dependencies=[Depends(require_owner)],
)
async def scan_stock(
    symbol: str,
    interval: str = "5m",
    session: AsyncSession = Depends(get_session),
) -> ScannerResultOut:
    """Legacy V1 single-stock scanner."""
    if interval not in {
        "1m",
        "5m",
        "15m",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "Scanner interval must be "
                "1m, 5m, or 15m"
            ),
        )

    instrument = await resolve_instrument(
        session,
        symbol,
    )

    try:
        candles = await market().candles(
            instrument.symbol,
            interval,
            instrument.token,
        )

        result = scan_symbol(
            symbol=instrument.symbol,
            candles=candles,
        )

        return ScannerResultOut(
            **result
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Scanner failed for "
                f"{symbol.upper()}: {exc}"
            ),
        ) from exc


@app.get(
    "/api/v2/scanner/{symbol}",
    response_model=ScannerV2Out,
    dependencies=[
        Depends(
            require_owner
        )
    ],
)
async def scan_stock_v2(
    symbol: str,
    interval: str = "5m",
    session: AsyncSession = Depends(
        get_session
    ),
) -> ScannerV2Out:

    """
    V2 single-stock scanner.

    Candle priority:

    1. Fresh market candles
    2. Permanent SQLite history
    3. Angel One historical fallback

    Scanner requires at least
    30 candles.
    """

    if interval not in {
        "1m",
        "5m",
        "15m",
    }:

        raise HTTPException(
            status_code=422,
            detail=(
                "Scanner interval must be "
                "1m, 5m, or 15m"
            ),
        )


    symbol_upper = (
        symbol
        .strip()
        .upper()
    )


    instrument = (
        await resolve_instrument(
            session,
            symbol_upper,
        )
    )


    try:

        # ==========================================
        # 1. LOAD PERMANENT STORED CANDLES
        # ==========================================

        stored_candles = (
            await load_candles(
                session,
                symbol=instrument.symbol,
                interval=interval,
                limit=200,
            )
        )


        # ==========================================
        # 2. TRY FRESH MARKET CANDLES
        # ==========================================

        fresh_candles = []


        try:

            fresh_candles = (
                await market()
                .candles(
                    instrument.symbol,
                    interval,
                    instrument.token,
                )
            )

        except Exception as exc:

            print(
                "Scanner live candle read failed:",
                instrument.symbol,
                interval,
                exc,
            )


        # ==========================================
        # 3. MERGE STORED + FRESH
        # ==========================================

        candle_map = {}


        for candle in stored_candles:

            candle_time = (
                candle.get(
                    "time"
                )
            )


            if (
                candle_time
                is not None
            ):

                candle_map[
                    int(
                        float(
                            candle_time
                        )
                    )
                ] = candle


        for candle in fresh_candles:

            candle_time = (
                candle.get(
                    "time"
                )
            )


            if (
                candle_time
                is not None
            ):

                candle_map[
                    int(
                        float(
                            candle_time
                        )
                    )
                ] = candle


        candles = sorted(
            candle_map.values(),
            key=lambda item:
                float(
                    item.get(
                        "time",
                        0,
                    )
                ),
        )


        candles = (
            candles[
                -200:
            ]
        )


        # ==========================================
        # 4. HISTORICAL FALLBACK
        # ==========================================

        if (
            len(candles) <
            30
        ):

            days_map = {
                "1m": 5,
                "5m": 10,
                "15m": 20,
            }


            days_to_fetch = (
                days_map[
                    interval
                ]
            )


            print(
                "Scanner historical fallback:",
                instrument.symbol,
                interval,
                days_to_fetch,
                "days",
            )


            historical = (
                await market()
                .historical_candles(
                    instrument.symbol,
                    interval,
                    instrument.token,
                    days=days_to_fetch,
                )
            )


            if historical:

                # Save permanently so
                # future scans do not
                # need another full fetch.

                await save_candles(
                    session,
                    symbol=instrument.symbol,
                    interval=interval,
                    candles=historical,
                )


                stored_candles = (
                    await load_candles(
                        session,
                        symbol=instrument.symbol,
                        interval=interval,
                        limit=200,
                    )
                )


                candle_map = {}


                for candle in stored_candles:

                    candle_time = (
                        candle.get(
                            "time"
                        )
                    )


                    if (
                        candle_time
                        is not None
                    ):

                        candle_map[
                            int(
                                float(
                                    candle_time
                                )
                            )
                        ] = candle


                for candle in fresh_candles:

                    candle_time = (
                        candle.get(
                            "time"
                        )
                    )


                    if (
                        candle_time
                        is not None
                    ):

                        candle_map[
                            int(
                                float(
                                    candle_time
                                )
                            )
                        ] = candle


                candles = sorted(
                    candle_map.values(),
                    key=lambda item:
                        float(
                            item.get(
                                "time",
                                0,
                            )
                        ),
                )


                candles = (
                    candles[
                        -200:
                    ]
                )


        # ==========================================
        # 5. VALIDATE
        # ==========================================

        if (
            len(candles) <
            30
        ):

            raise ValueError(
                (
                    "Not enough candles "
                    f"for {instrument.symbol} "
                    f"{interval}; "
                    f"received "
                    f"{len(candles)}"
                )
            )


        # ==========================================
        # 6. RUN AI SCANNER
        # ==========================================

        result = scan_symbol(
            symbol=
                instrument.symbol,

            candles=
                candles,
        )


        return (
            build_scanner_v2_response(
                result=result,
                interval=interval,
            )
        )


    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(
                exc
            ),
        ) from exc


    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "V2 scanner failed for "
                f"{symbol_upper}: "
                f"{exc}"
            ),
        ) from exc


@app.get(
    "/api/v2/market-scanner",
    dependencies=[Depends(require_owner)],
)
async def scan_market_v2(
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    Scan the full watchlist across 1m, 5m, and 15m.

    Prefer candles already maintained by LiveCandleEngine.
    If local candles are insufficient, use SmartAPI
    historical candles through a serialized fallback.
    """
    items = list(
        (
            await session.execute(
                select(WatchlistItem).order_by(
                    WatchlistItem.symbol
                )
            )
        ).scalars()
    )

    if not items:
        return {
            "scanned": 0,
            "successful": 0,
            "failed": 0,
            "opportunities": [],
            "failures": [],
        }

    instruments = [
        ScanInstrument(
            symbol=item.symbol,
            token=item.token,
            name=item.name,
        )
        for item in items
    ]

    historical_lock = asyncio.Lock()

    async def fetch_candles(
        symbol: str,
        timeframe: str,
        token: Optional[str],
    ) -> list[dict[str, Any]]:
        live_engine = getattr(
            app.state,
            "live_candles",
            None,
        )

        if live_engine is not None:
            candles_method = getattr(
                live_engine,
                "candles",
                None,
            )

            if callable(candles_method):
                try:
                    local_candles = candles_method(
                        symbol,
                        timeframe,
                        limit=200,
                    )

                    if len(local_candles) >= 30:
                        return local_candles

                except Exception as exc:
                    print(
                        "Local candle read failed:",
                        symbol,
                        timeframe,
                        exc,
                    )

        if not token:
            raise RuntimeError(
                f"Missing instrument token for {symbol}"
            )

        async with historical_lock:
            if live_engine is not None:
                candles_method = getattr(
                    live_engine,
                    "candles",
                    None,
                )

                if callable(candles_method):
                    try:
                        local_candles = candles_method(
                            symbol,
                            timeframe,
                            limit=200,
                        )

                        if len(local_candles) >= 30:
                            return local_candles

                    except Exception:
                        pass

            days_map = {
                "1m": 2,
                "5m": 5,
                "15m": 10,
            }

            days = days_map.get(
                timeframe,
                5,
            )

            print(
                "Historical candle fallback:",
                symbol,
                timeframe,
                f"{days} days",
            )

            historical = (
                await market().historical_candles(
                    symbol,
                    timeframe,
                    token,
                    days=days,
                )
            )

            if not historical:
                raise RuntimeError(
                    "No historical candles returned "
                    f"for {symbol} {timeframe}"
                )

            historical = historical[-200:]

            if live_engine is not None:
                seed_method = getattr(
                    live_engine,
                    "seed",
                    None,
                )

                if callable(seed_method):
                    try:
                        seed_method(
                            symbol=symbol,
                            timeframe=timeframe,
                            candles=historical,
                        )
                    except Exception as exc:
                        print(
                            "Unable to seed local candles:",
                            symbol,
                            timeframe,
                            exc,
                        )

            await asyncio.sleep(0.45)

            return historical

    result = await run_market_scan(
        instruments=instruments,
        fetch_candles=fetch_candles,
        concurrency=2,
    )

    return market_scan_to_dict(
        result
    )


@app.get(
    "/api/live/candles/{symbol}",
    dependencies=[Depends(require_owner)],
)
async def get_live_candles(
    symbol: str,
    interval: str = "5m",
    session: AsyncSession = Depends(
        get_session
    ),
) -> dict[str, Any]:

    symbol_upper = (
        symbol
        .strip()
        .upper()
    )

    allowed = {
        "15s",
        "1m",
        "5m",
        "15m",
        "1D",
        "1W",
        "1M",
    }

    if interval not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                "Interval must be "
                "15s, 1m, 5m, 15m, "
                "1D, 1W or 1M"
            ),
        )

    engine = getattr(
        app.state,
        "live_candles",
        None,
    )

    if engine is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Live candle engine "
                "is not available"
            ),
        )

    instrument = await resolve_instrument(
        session,
        symbol_upper,
    )

    provider = market()

    # ==============================================
    # 15 SECOND LIVE CANDLES
    # ==============================================

    if interval == "15s":

        snapshot = (
            engine.snapshot(
                symbol_upper
            )
        )

        return {
            "symbol":
                instrument.symbol,

            "15s":
                snapshot.get(
                    "15s",
                    [],
                ),
        }

    try:

        # ==========================================
        # 1 MINUTE
        # ==========================================

        if interval == "1m":

            latest = await latest_candle_time(
                session,
                symbol=instrument.symbol,
                interval="1m",
            )

            # First-ever load: fetch a few days.
            # Later loads: only fetch a small overlapping
            # window so new candles are appended.
            if latest is None:
                days_to_fetch = 5
            else:
                now_utc = datetime.now(
                    timezone.utc
                )

                elapsed_days = max(
                    1,
                    (
                        now_utc
                        - latest
                    ).days
                    + 1,
                )

                # Keep the incremental request small,
                # but include overlap for safe updates.
                days_to_fetch = min(
                    max(
                        elapsed_days,
                        2,
                    ),
                    5,
                )

            candles = await (
                provider
                .historical_candles(
                    instrument.symbol,
                    "1m",
                    instrument.token,
                    days=days_to_fetch,
                )
            )

            await save_candles(
                session,
                symbol=instrument.symbol,
                interval="1m",
                candles=candles,
            )

            stored = await load_candles(
                session,
                symbol=instrument.symbol,
                interval="1m",
            )

            return {
                "symbol":
                    instrument.symbol,
                "1m":
                    stored,
            }

        # ==========================================
        # 5 MINUTES
        # ==========================================

        if interval == "5m":

            latest = await latest_candle_time(
                session,
                symbol=instrument.symbol,
                interval="5m",
            )

            if latest is None:
                days_to_fetch = 10
            else:
                now_utc = datetime.now(
                    timezone.utc
                )

                elapsed_days = max(
                    1,
                    (
                        now_utc
                        - latest
                    ).days
                    + 1,
                )

                days_to_fetch = min(
                    max(
                        elapsed_days,
                        2,
                    ),
                    10,
                )

            candles = await (
                provider
                .historical_candles(
                    instrument.symbol,
                    "5m",
                    instrument.token,
                    days=days_to_fetch,
                )
            )

            await save_candles(
                session,
                symbol=instrument.symbol,
                interval="5m",
                candles=candles,
            )

            stored = await load_candles(
                session,
                symbol=instrument.symbol,
                interval="5m",
            )

            return {
                "symbol":
                    instrument.symbol,
                "5m":
                    stored,
            }

        # ==========================================
        # 15 MINUTES
        # ==========================================

        if interval == "15m":

            latest = await latest_candle_time(
                session,
                symbol=instrument.symbol,
                interval="15m",
            )

            if latest is None:
                days_to_fetch = 30
            else:
                now_utc = datetime.now(
                    timezone.utc
                )

                elapsed_days = max(
                    1,
                    (
                        now_utc
                        - latest
                    ).days
                    + 1,
                )

                days_to_fetch = min(
                    max(
                        elapsed_days,
                        2,
                    ),
                    30,
                )

            candles = await (
                provider
                .historical_candles(
                    instrument.symbol,
                    "15m",
                    instrument.token,
                    days=days_to_fetch,
                )
            )

            await save_candles(
                session,
                symbol=instrument.symbol,
                interval="15m",
                candles=candles,
            )

            stored = await load_candles(
                session,
                symbol=instrument.symbol,
                interval="15m",
            )

            return {
                "symbol":
                    instrument.symbol,
                "15m":
                    stored,
            }


        # ==========================================
        # DAILY
        # ==========================================

        if interval == "1D":

            latest = await latest_candle_time(
                session,
                symbol=instrument.symbol,
                interval="1D",
            )

            if latest is None:
                days_to_fetch = 365
            else:
                now_utc = datetime.now(
                    timezone.utc
                )

                elapsed_days = max(
                    1,
                    (
                        now_utc
                        - latest
                    ).days
                    + 1,
                )

                days_to_fetch = min(
                    max(
                        elapsed_days,
                        2,
                    ),
                    365,
                )

            daily = await (
                provider
                .historical_candles(
                    instrument.symbol,
                    "1D",
                    instrument.token,
                    days=days_to_fetch,
                )
            )

            await save_candles(
                session,
                symbol=instrument.symbol,
                interval="1D",
                candles=daily,
            )

            stored = await load_candles(
                session,
                symbol=instrument.symbol,
                interval="1D",
            )

            return {
                "symbol":
                    instrument.symbol,
                "1D":
                    stored,
            }
        # ==========================================
        # WEEKLY
        # ==========================================

        if interval == "1W":

            stored_daily = await load_candles(
                session,
                symbol=instrument.symbol,
                interval="1D",
            )

            # About 5 years of trading days.
            # Backfill only when we do not yet have
            # enough permanent daily history.
            if len(stored_daily) < 1000:

                daily_history = await (
                    provider
                    .long_daily_history(
                        instrument.symbol,
                        instrument.token,
                        days=365 * 5,
                    )
                )

                await save_candles(
                    session,
                    symbol=instrument.symbol,
                    interval="1D",
                    candles=daily_history,
                )

                stored_daily = await load_candles(
                    session,
                    symbol=instrument.symbol,
                    interval="1D",
                )

            weekly = aggregate_weekly(
                stored_daily
            )

            return {
                "symbol":
                    instrument.symbol,

                "1W":
                    weekly,
            }

        # ==========================================
        # MONTHLY
        # ==========================================

        if interval == "1M":

            stored_daily = await load_candles(
                session,
                symbol=instrument.symbol,
                interval="1D",
            )

            print(
                "[1M] Stored daily before backfill:",
                instrument.symbol,
                len(stored_daily),
            )

            if len(stored_daily) < 2000:

                print(
                    "[1M] Starting 10-year backfill:",
                    instrument.symbol,
                )

                daily_history = await (
                    provider
                    .long_daily_history(
                        instrument.symbol,
                        instrument.token,
                        days=365 * 10,
                    )
                )

                print(
                    "[1M] Angel One returned:",
                    len(daily_history),
                    "daily candles",
                )

                saved_count = await save_candles(
                    session,
                    symbol=instrument.symbol,
                    interval="1D",
                    candles=daily_history,
                )

                print(
                    "[1M] New DB rows saved:",
                    saved_count,
                )

                stored_daily = await load_candles(
                    session,
                    symbol=instrument.symbol,
                    interval="1D",
                )

                print(
                    "[1M] Stored daily after backfill:",
                    len(stored_daily),
                )

            monthly = aggregate_monthly(
                stored_daily
            )

            print(
                "[1M] Monthly candles:",
                len(monthly),
            )

            return {
                "symbol":
                    instrument.symbol,

                "1M":
                    monthly,
            }
    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Live candle fetch failed "
                f"for {symbol_upper} "
                f"({interval}): {exc}"
            ),
        ) from exc

    symbol_upper = (
        symbol
        .strip()
        .upper()
    )

    allowed = {
        "15s",
        "1m",
        "5m",
        "15m",
        "1D",
        "1W",
        "1M",
    }

    if interval not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                "Interval must be "
                "15s, 1m, 5m, 15m, "
                "1D, 1W or 1M"
            ),
        )

    engine = getattr(
        app.state,
        "live_candles",
        None,
    )

    if engine is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Live candle engine "
                "is not available"
            ),
        )

    instrument = await resolve_instrument(
        session,
        symbol_upper,
    )

    provider = market()

    live_snapshot = (
        engine.snapshot(
            symbol_upper
        )
    )

    fifteen_second = (
        live_snapshot.get(
            "15s",
            [],
        )
    )
    try:
        one_minute = (
            await provider
            .historical_candles(
                instrument.symbol,
                "1m",
                instrument.token,
                2,
            )
        )

        await asyncio.sleep(
            0.4
        )

        five_minute = (
            await provider
            .historical_candles(
                instrument.symbol,
                "5m",
                instrument.token,
                5,
            )
        )

        await asyncio.sleep(
            0.4
        )

        fifteen_minute = (
            await provider
            .historical_candles(
                instrument.symbol,
                "15m",
                instrument.token,
                10,
            )
        )

        await asyncio.sleep(
            0.4
        )

        daily = (
            await provider
            .historical_candles(
                instrument.symbol,
                "1D",
                instrument.token,
                365,
            )
        )

        weekly = aggregate_weekly(
            daily
        )

        monthly = aggregate_monthly(
            daily
        )

        return {
            "symbol":
                instrument.symbol,

            "15s":
                fifteen_second,

            "1m":
                one_minute,

            "5m":
                five_minute,

            "15m":
                fifteen_minute,

            "1D":
                daily,

            "1W":
                weekly,

            "1M":
                monthly,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Live candle fetch "
                f"failed for "
                f"{symbol_upper}: {exc}"
            ),
        ) from exc

@app.websocket("/api/ws/market")
async def market_socket(
    websocket: WebSocket,
) -> None:

    await websocket.accept()

    if websocket.session.get("owner") is not True:
        await websocket.close(code=4401)
        return

    try:

        while True:

            live_market = getattr(
                app.state,
                "live_market",
                None,
            )

            if live_market is None:

                await websocket.send_json(
                    {
                        "type": "market_status",
                        "status": "offline",
                        "time": (
                            datetime.utcnow()
                            .isoformat()
                        ),
                    }
                )

            else:

                snapshot = (
                    live_market.snapshot()
                )

                await websocket.send_json(
                    {
                        "type": "market_update",
                        "status": (
                            "live"
                            if live_market.running
                            else "offline"
                        ),
                        "stocks": snapshot,
                        "count": len(snapshot),
                        "time": (
                            datetime.utcnow()
                            .isoformat()
                        ),
                    }
                )

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        return