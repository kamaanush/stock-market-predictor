import asyncio
import csv
import hmac
import io
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Optional, Union

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .database import SessionLocal, get_session, initialize_database
from .market import IST, DemoMarketData, Quote, create_market_data
from .models import Alert, AlertEvent, ImportBatch, Instrument, PortfolioHolding, WatchlistItem
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
from .services.scanner import scan_symbol
from .services.scanner_v2 import (
    build_scanner_v2_response,
)

SCRIP_MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_database()
    await seed_demo_instruments()
    try:
        app.state.market = create_market_data(get_settings())
        app.state.market_warning = ""
    except Exception:
        # Credentials are optional in v1 and a failed live login must not stop the
        # private dashboard from working in clearly labelled demo mode.
        app.state.market = DemoMarketData()
        app.state.market_warning = "SmartAPI connection failed; using demo market data."
    alert_worker = asyncio.create_task(alert_worker_loop(app))
    try:
        yield
    finally:
        alert_worker.cancel()
        with suppress(asyncio.CancelledError):
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
            existing = (await session.execute(select(Instrument).where(Instrument.symbol == symbol))).scalar_one_or_none()
            if existing is None:
                session.add(Instrument(exchange="NSE", symbol=symbol, name=name, token=token, kind=kind))
        await session.commit()


async def alert_worker_loop(app: FastAPI) -> None:
    """Evaluate price alerts periodically while the local backend is running."""
    while True:
        try:
            await evaluate_alerts_once(app)
        except Exception:
            # An unavailable provider or a malformed user alert should not stop
            # the tracker. The next interval retries remaining active alerts.
            pass
        await asyncio.sleep(10)


async def evaluate_alerts_once(app: FastAPI) -> None:
    telegram_messages: list[str] = []
    async with SessionLocal() as session:
        alerts = list((await session.execute(select(Alert).where(Alert.active.is_(True)))).scalars())
        for alert in alerts:
            try:
                instrument = await resolve_instrument(session, alert.symbol)
                quote = await app.state.market.quote(alert.symbol, instrument.token)
            except Exception:
                continue
            triggered = (alert.condition == "ABOVE" and quote.last_price >= alert.target_price) or (alert.condition == "BELOW" and quote.last_price <= alert.target_price)
            if not triggered:
                continue
            message = f"{alert.symbol} is {quote.last_price:,.2f}: alert {alert.condition.lower()} {alert.target_price:,.2f} triggered."
            session.add(AlertEvent(alert_id=alert.id, symbol=alert.symbol, message=message, delivery=alert.delivery))
            alert.active = False
            alert.last_triggered_at = datetime.now(IST)
            if alert.delivery in {"TELEGRAM", "BOTH"}:
                telegram_messages.append(message)
        await session.commit()
    for message in telegram_messages:
        try:
            await send_telegram(settings, message)
        except Exception:
            # The browser event remains available even when Telegram is offline.
            pass


app = FastAPI(title="NSE Stock Tracker API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret or "development-only-change-me", same_site="lax", https_only=False)
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
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")


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


async def resolve_instrument(session: AsyncSession, symbol: str) -> Union[Instrument, WatchlistItem, PortfolioHolding]:
    result = await session.execute(select(Instrument).where(Instrument.symbol == symbol.upper()))
    instrument = result.scalar_one_or_none()
    if instrument:
        return instrument
    result = await session.execute(select(WatchlistItem).where(WatchlistItem.symbol == symbol.upper()))
    item = result.scalar_one_or_none()
    if item:
        return item
    result = await session.execute(select(PortfolioHolding).where(PortfolioHolding.symbol == symbol.upper()))
    holding = result.scalar_one_or_none()
    if holding:
        return holding
    raise HTTPException(status_code=404, detail=f"Unknown symbol: {symbol}")


@app.get("/api/health")
async def health() -> dict[str, Union[bool, str]]:
    return {"status": "ok", "market_mode": "demo" if isinstance(market(), DemoMarketData) else "smartapi", "smartapi_configured": settings.smartapi_ready, "market_warning": app.state.market_warning}


@app.post("/api/auth/login")
async def login(payload: LoginRequest, request: Request) -> dict[str, bool]:
    if not settings.app_password:
        raise HTTPException(status_code=503, detail="APP_PASSWORD is not configured")
    if not hmac.compare_digest(payload.password, settings.app_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    request.session.clear()
    request.session["owner"] = True
    return {"ok": True}


@app.post("/api/auth/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth/me")
async def me(request: Request) -> dict[str, bool]:
    return {"authenticated": request.session.get("owner") is True}


@app.get("/api/instruments/search", response_model=list[InstrumentOut], dependencies=[Depends(require_owner)])
async def search_instruments(q: str, session: AsyncSession = Depends(get_session)) -> list[Instrument]:
    term = q.strip().upper()
    if len(term) < 1:
        return []
    query = select(Instrument).where(Instrument.symbol.ilike(f"%{term}%") | Instrument.name.ilike(f"%{term}%")).limit(30)
    return list((await session.execute(query)).scalars())


@app.post("/api/instruments/refresh", dependencies=[Depends(require_owner)])
async def refresh_instruments(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
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
        # Equity plus recognised index records; derivatives are deliberately excluded.
        if instrument_type not in {"", "EQ", "AMXIDX"} and not symbol.endswith("-EQ"):
            continue
        clean_symbol = symbol.removesuffix("-EQ")
        if clean_symbol in seen_symbols:
            continue
        seen_symbols.add(clean_symbol)
        instruments.append(Instrument(exchange="NSE", symbol=clean_symbol, name=str(row.get("name") or clean_symbol), token=token, kind="INDEX" if instrument_type == "AMXIDX" else "EQUITY"))
    session.add_all(instruments)
    await session.commit()
    return {"imported": len(instruments)}


@app.get("/api/watchlist", response_model=list[WatchlistOut], dependencies=[Depends(require_owner)])
async def get_watchlist(session: AsyncSession = Depends(get_session)) -> list[WatchlistOut]:
    items = list((await session.execute(select(WatchlistItem).order_by(WatchlistItem.symbol))).scalars())
    quotes = await asyncio.gather(*(market().quote(item.symbol, item.token) for item in items))
    by_symbol = {quote.symbol: quote for quote in quotes}
    return [WatchlistOut(symbol=item.symbol, name=item.name, token=item.token, kind=item.kind, last_price=by_symbol[item.symbol].last_price, change_percent=by_symbol[item.symbol].change_percent) for item in items]


@app.post("/api/watchlist", response_model=WatchlistOut, dependencies=[Depends(require_owner)], status_code=201)
async def add_watchlist(payload: WatchlistCreate, session: AsyncSession = Depends(get_session)) -> WatchlistOut:
    symbol = payload.symbol.upper()
    existing = (await session.execute(select(WatchlistItem).where(WatchlistItem.symbol == symbol))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Symbol is already in the watchlist")
    item = WatchlistItem(symbol=symbol, name=payload.name, token=payload.token, kind=payload.kind)
    session.add(item)
    await session.commit()
    quote = await market().quote(item.symbol, item.token)
    return WatchlistOut(symbol=item.symbol, name=item.name, token=item.token, kind=item.kind, last_price=quote.last_price, change_percent=quote.change_percent)


@app.delete("/api/watchlist/{symbol}", status_code=204, dependencies=[Depends(require_owner)])
async def remove_watchlist(symbol: str, session: AsyncSession = Depends(get_session)) -> None:
    result = await session.execute(delete(WatchlistItem).where(WatchlistItem.symbol == symbol.upper()))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Watchlist symbol not found")
    await session.commit()


@app.get("/api/stocks/{symbol}/quote", response_model=QuoteOut, dependencies=[Depends(require_owner)])
async def get_quote(symbol: str, session: AsyncSession = Depends(get_session)) -> QuoteOut:
    instrument = await resolve_instrument(session, symbol)
    return quote_out(await market().quote(instrument.symbol, instrument.token))

@app.get(
    "/api/v2/scanner/{symbol}",
    response_model=ScannerV2Out,
    dependencies=[Depends(require_owner)],
)
async def scan_stock_v2(
    symbol: str,
    interval: str = "5m",
    session: AsyncSession = Depends(get_session),
) -> ScannerV2Out:
    if interval not in {"1m", "5m", "15m"}:
        raise HTTPException(
            status_code=422,
            detail="Scanner interval must be 1m, 5m, or 15m",
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

        return build_scanner_v2_response(
         result=result,
         interval=interval,
        )


        ema_status = (
            "BUY"
            if result["ema_fast"] > result["ema_slow"]
            else "SELL"
            if result["ema_fast"] < result["ema_slow"]
            else "NEUTRAL"
        )

        supertrend_status = (
            "BUY"
            if result["supertrend_direction"]
            else "SELL"
        )

        macd_status = (
            "BUY"
            if result["macd"] > result["macd_signal"]
            else "SELL"
            if result["macd"] < result["macd_signal"]
            else "NEUTRAL"
        )

        vwap_status = (
            "ABOVE"
            if result["last_price"] > result["vwap"]
            else "BELOW"
            if result["last_price"] < result["vwap"]
            else "AT VWAP"
        )

        high_volume = (
            result["average_volume"] > 0
            and result["volume"]
            >= result["average_volume"] * 1.2
        )

        volume_status = (
            "HIGH"
            if high_volume
            else "NORMAL"
        )

        adx = result["adx"]

        if adx >= 25:
            trend_strength = "STRONG"
        elif adx >= 20:
            trend_strength = "DEVELOPING"
        else:
            trend_strength = "WEAK"

        entry = result.get("entry_price")
        stoploss = result.get("stoploss")
        target2 = result.get("target2")

        risk_reward = None

        if (
            entry is not None
            and stoploss is not None
            and target2 is not None
        ):
            risk = abs(entry - stoploss)
            reward = abs(target2 - entry)

            if risk > 0:
                risk_reward = (
                    f"1:{round(reward / risk, 2)}"
                )

        score = int(result["score"])

        if score >= 90:
            probability_label = "VERY HIGH"
        elif score >= 80:
            probability_label = "HIGH"
        elif score >= 70:
            probability_label = "MODERATE"
        else:
            probability_label = "LOW"

        if trend_strength == "WEAK":
            risk_label = "HIGH"
        elif result["action_status"] in {
            "EXTENDED",
            "AVOID",
        }:
            risk_label = "HIGH"
        elif result["action_status"] in {
            "WAIT BREAKOUT",
            "WAIT BREAKDOWN",
        }:
            risk_label = "MEDIUM"
        else:
            risk_label = "LOW"

        summary = (
            f"{result['signal']} setup with "
            f"{trend_strength.lower()} trend strength. "
            f"Current status is "
            f"{result['action_status']}."
        )

        return ScannerV2Out(
            symbol=result["symbol"],
            signal=result["signal"],
            score=score,
            grade=result["grade"],
            trend=result["trend"],
            reason=result["reason"],

            technical_analysis={
                "ema": ema_status,
                "ema_fast": result["ema_fast"],
                "ema_slow": result["ema_slow"],

                "supertrend": supertrend_status,
                "supertrend_value": result["supertrend"],

                "adx": result["adx"],
                "plus_di": result["plus_di"],
                "minus_di": result["minus_di"],
                "trend_strength": trend_strength,

                "rsi": result["rsi"],

                "macd": macd_status,
                "macd_value": result["macd"],
                "macd_signal": result["macd_signal"],

                "vwap": vwap_status,
                "vwap_value": result["vwap"],

                "volume": volume_status,
                "volume_value": result["volume"],
                "average_volume": result[
                    "average_volume"
                ],

                "atr": result["atr"],

                "pattern": result.get("pattern"),
                "pattern_direction": result.get(
                    "pattern_direction"
                ),
                "pattern_confidence": result.get(
                    "pattern_confidence"
                ),
            },

            trade_plan={
                "entry": result.get("entry_price"),
                "stoploss": result.get("stoploss"),
                "target1": result.get("target1"),
                "target2": result.get("target2"),
                "risk_reward": risk_reward,
            },

            analysis={
                "engine": "RULE_ENGINE_V2",
                "confidence": score,
                "probability_label": probability_label,
                "risk_label": risk_label,
                "summary": summary,
            },

            execution={
                "status": result["action_status"],
                "timeframe": interval,
                "last_price": result["last_price"],
            },
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
                f"V2 scanner failed for "
                f"{symbol.upper()}: {exc}"
            ),
        ) from exc

@app.get("/api/stocks/{symbol}/candles", response_model=list[CandleOut], dependencies=[Depends(require_owner)])
async def get_candles(symbol: str, interval: str = "5m", session: AsyncSession = Depends(get_session)) -> list[dict[str, float]]:
    if interval not in {"15s", "1m", "5m", "15m"}:
        raise HTTPException(status_code=422, detail="Interval must be 15s, 1m, 5m, or 15m")
    instrument = await resolve_instrument(session, symbol)
    return await market().candles(instrument.symbol, interval, instrument.token)


@app.get("/api/portfolio/holdings", response_model=list[HoldingOut], dependencies=[Depends(require_owner)])
async def get_holdings(session: AsyncSession = Depends(get_session)) -> list[HoldingOut]:
    holdings = list((await session.execute(select(PortfolioHolding).order_by(PortfolioHolding.symbol))).scalars())
    quotes = await asyncio.gather(*(market().quote(item.symbol, item.token) for item in holdings))
    quotes_by_symbol = {quote.symbol: quote for quote in quotes}
    output: list[HoldingOut] = []
    for holding in holdings:
        current = quotes_by_symbol[holding.symbol].last_price
        invested = holding.quantity * holding.average_price
        market_value = holding.quantity * current
        pnl = market_value - invested
        output.append(HoldingOut(symbol=holding.symbol, name=holding.name, token=holding.token, quantity=holding.quantity, average_price=holding.average_price, current_price=current, market_value=round(market_value, 2), unrealized_pnl=round(pnl, 2), unrealized_pnl_percent=round(pnl / invested * 100, 2)))
    return output


@app.put("/api/portfolio/holdings", response_model=HoldingOut, dependencies=[Depends(require_owner)])
async def upsert_holding(payload: HoldingInput, session: AsyncSession = Depends(get_session)) -> HoldingOut:
    symbol = payload.symbol.upper()
    holding = (await session.execute(select(PortfolioHolding).where(PortfolioHolding.symbol == symbol))).scalar_one_or_none()
    if holding is None:
        holding = PortfolioHolding(**payload.model_dump(exclude={"symbol"}), symbol=symbol)
        session.add(holding)
    else:
        for key, value in payload.model_dump(exclude={"symbol"}).items():
            setattr(holding, key, value)
    await session.commit()
    current = (await market().quote(holding.symbol, holding.token)).last_price
    invested = holding.quantity * holding.average_price
    value = holding.quantity * current
    pnl = value - invested
    return HoldingOut(symbol=holding.symbol, name=holding.name, token=holding.token, quantity=holding.quantity, average_price=holding.average_price, current_price=current, market_value=round(value, 2), unrealized_pnl=round(pnl, 2), unrealized_pnl_percent=round(pnl / invested * 100, 2))


@app.post("/api/portfolio/import", dependencies=[Depends(require_owner)])
async def import_holdings(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Upload a CSV file")
    try:
        rows = list(csv.DictReader(io.StringIO((await file.read()).decode("utf-8-sig"))))
        required = {"symbol", "name", "quantity", "average_price"}
        if not rows or not required.issubset(rows[0]):
            raise ValueError("CSV headers must include symbol,name,quantity,average_price; token is optional")
        for row in rows:
            symbol = row["symbol"].strip().upper()
            holding = (await session.execute(select(PortfolioHolding).where(PortfolioHolding.symbol == symbol))).scalar_one_or_none()
            values = {"name": row["name"].strip(), "token": row.get("token", "").strip(), "quantity": float(row["quantity"]), "average_price": float(row["average_price"])}
            if values["quantity"] <= 0 or values["average_price"] <= 0:
                raise ValueError(f"{symbol}: quantity and average_price must be positive")
            if holding is None:
                session.add(PortfolioHolding(symbol=symbol, **values))
            else:
                for key, value in values.items():
                    setattr(holding, key, value)
        session.add(ImportBatch(filename=file.filename, row_count=len(rows)))
        await session.commit()
        return {"imported": len(rows)}
    except (UnicodeDecodeError, ValueError, KeyError) as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/alerts", response_model=list[AlertOut], dependencies=[Depends(require_owner)])
async def get_alerts(session: AsyncSession = Depends(get_session)) -> list[Alert]:
    return list((await session.execute(select(Alert).order_by(Alert.id.desc()))).scalars())


@app.get("/api/alerts/events", response_model=list[AlertEventOut], dependencies=[Depends(require_owner)])
async def get_alert_events(after_id: int = 0, session: AsyncSession = Depends(get_session)) -> list[AlertEvent]:
    return list((await session.execute(select(AlertEvent).where(AlertEvent.id > after_id).order_by(AlertEvent.id))).scalars())


@app.post("/api/alerts", response_model=AlertOut, status_code=201, dependencies=[Depends(require_owner)])
async def create_alert(payload: AlertInput, session: AsyncSession = Depends(get_session)) -> Alert:
    alert = Alert(**payload.model_dump(), symbol=payload.symbol.upper())
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


@app.patch("/api/alerts/{alert_id}", response_model=AlertOut, dependencies=[Depends(require_owner)])
async def toggle_alert(alert_id: int, active: bool, session: AsyncSession = Depends(get_session)) -> Alert:
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.active = active
    await session.commit()
    await session.refresh(alert)
    return alert


@app.delete("/api/alerts/{alert_id}", status_code=204, dependencies=[Depends(require_owner)])
async def delete_alert(alert_id: int, session: AsyncSession = Depends(get_session)) -> None:
    alert = await session.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await session.delete(alert)
    await session.commit()


@app.websocket("/api/ws/market")
async def market_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    if websocket.session.get("owner") is not True:
        await websocket.close(code=4401)
        return
    try:
        while True:
            await websocket.send_json({"type": "heartbeat", "time": datetime.utcnow().isoformat()})
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        return
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
    if interval not in {"1m", "5m", "15m"}:
        raise HTTPException(
            status_code=422,
            detail="Scanner interval must be 1m, 5m, or 15m",
        )

    instrument = await resolve_instrument(session, symbol)

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

        return ScannerResultOut(**result)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Scanner failed for {symbol.upper()}: {exc}",
        ) from exc


@app.get(
    "/api/scanner/watchlist",
    response_model=list[ScannerResultOut],
    dependencies=[Depends(require_owner)],
)
async def scan_watchlist(
    interval: str = "5m",
    session: AsyncSession = Depends(get_session),
) -> list[ScannerResultOut]:
    if interval not in {"1m", "5m", "15m"}:
        raise HTTPException(
            status_code=422,
            detail="Scanner interval must be 1m, 5m, or 15m",
        )

    items = list(
        (
            await session.execute(
                select(WatchlistItem).order_by(WatchlistItem.symbol)
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

            results.append(ScannerResultOut(**result))

        except Exception:
            continue

    return sorted(
        results,
        key=lambda item: item.score,
        reverse=True,
    )
