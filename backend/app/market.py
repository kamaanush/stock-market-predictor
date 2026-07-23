import asyncio
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pyotp

from .config import Settings

IST = timezone(timedelta(hours=5, minutes=30))
INTERVAL_MAP = {"1m": "ONE_MINUTE", "5m": "FIVE_MINUTE", "15m": "FIFTEEN_MINUTE"}


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
        return round(((self.last_price - self.previous_close) / self.previous_close) * 100, 2)


class FifteenSecondAggregator:
    """Keeps only today's in-process candles; no historic 15-second data is promised."""

    def __init__(self) -> None:
        self.candles: dict[str, dict[int, dict[str, float]]] = {}

    def ingest(self, symbol: str, price: float, timestamp: datetime | None = None) -> dict[str, float]:
        now = (timestamp or datetime.now(IST)).astimezone(IST)
        bucket = int(now.timestamp()) // 15 * 15
        series = self.candles.setdefault(symbol, {})
        candle = series.get(bucket)
        if candle is None:
            candle = {"time": bucket, "open": price, "high": price, "low": price, "close": price, "volume": 0}
            series[bucket] = candle
        else:
            candle["high"] = max(candle["high"], price)
            candle["low"] = min(candle["low"], price)
            candle["close"] = price
        return candle

    def series(self, symbol: str) -> list[dict[str, float]]:
        return list(self.candles.get(symbol, {}).values())


class DemoMarketData:
    """Safe local fallback used until complete SmartAPI credentials are configured."""

    base_prices = {"RELIANCE": 1422.8, "TCS": 3310.5, "INFY": 1512.4, "HDFCBANK": 1917.6, "NIFTY 50": 24801.3}

    def __init__(self) -> None:
        self.aggregator = FifteenSecondAggregator()

    async def quote(self, symbol: str, token: str = "") -> Quote:
        now = datetime.now(IST)
        base = self.base_prices.get(symbol.upper(), 1000.0)
        phase = now.timestamp() / 20 + sum(ord(char) for char in symbol)
        last = round(base * (1 + math.sin(phase) * 0.0015), 2)
        quote = Quote(symbol=symbol, last_price=last, open=round(base * 0.998, 2), high=round(base * 1.005, 2), low=round(base * 0.995, 2), previous_close=base, updated_at=now)
        self.aggregator.ingest(symbol, quote.last_price, now)
        return quote

    async def candles(self, symbol: str, interval: str, token: str = "") -> list[dict[str, float]]:
        if interval == "15s":
            await self.quote(symbol, token)
            return self.aggregator.series(symbol)
        seconds = {"1m": 60, "5m": 300, "15m": 900}[interval]
        now = datetime.now(IST)
        base = self.base_prices.get(symbol.upper(), 1000.0)
        output: list[dict[str, float]] = []
        for index in range(120):
            timestamp = now - timedelta(seconds=seconds * (120 - index))
            pivot = base * (1 + math.sin(index / 8) * 0.012)
            open_price = round(pivot * (1 + math.sin(index) * 0.001), 2)
            close = round(pivot * (1 + math.cos(index) * 0.001), 2)
            output.append({"time": int(timestamp.timestamp()), "open": open_price, "high": round(max(open_price, close) * 1.002, 2), "low": round(min(open_price, close) * 0.998, 2), "close": close, "volume": 10000 + index * 120})
        return output


class AngelOneMarketData:
    """Read-only SmartAPI HTTP client. Live streaming is wired in the service layer next."""

    def __init__(self, settings: Settings) -> None:
        from SmartApi import SmartConnect

        self.settings = settings
        self.client = SmartConnect(api_key=settings.smartapi_api_key)
        self._login()
        self.aggregator = FifteenSecondAggregator()

    def _login(self) -> None:
        totp = pyotp.TOTP(self.settings.smartapi_totp_secret).now()
        response = self.client.generateSession(self.settings.smartapi_client_code, self.settings.smartapi_pin, totp)
        if not response.get("status"):
            raise RuntimeError(f"SmartAPI login failed: {response.get('message', 'unknown error')}")

    async def quote(self, symbol: str, token: str) -> Quote:
        def fetch() -> Quote:
            response = self.client.ltpData("NSE", symbol, token)
            if not response.get("status"):
                raise RuntimeError(response.get("message", "Unable to fetch quote"))
            data = response["data"]
            price = float(data["ltp"])
            return Quote(symbol=symbol, last_price=price, open=float(data.get("open", price)), high=float(data.get("high", price)), low=float(data.get("low", price)), previous_close=float(data.get("close", price)), updated_at=datetime.now(IST))

        quote = await asyncio.to_thread(fetch)
        self.aggregator.ingest(symbol, quote.last_price, quote.updated_at)
        return quote

    async def candles(self, symbol: str, interval: str, token: str) -> list[dict[str, float]]:
        if interval == "15s":
            await self.quote(symbol, token)
            return self.aggregator.series(symbol)
        if interval not in INTERVAL_MAP:
            raise ValueError("Unsupported interval")

        def fetch() -> list[dict[str, float]]:
            now = datetime.now(IST)
            response = self.client.historicalCandleData({
                "exchange": "NSE",
                "symboltoken": token,
                "interval": INTERVAL_MAP[interval],
                "fromdate": (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
                "todate": now.strftime("%Y-%m-%d %H:%M"),
            })
            if not response.get("status"):
                raise RuntimeError(response.get("message", "Unable to fetch candles"))
            return [
                {"time": int(datetime.fromisoformat(row[0].replace("Z", "+00:00")).timestamp()), "open": float(row[1]), "high": float(row[2]), "low": float(row[3]), "close": float(row[4]), "volume": float(row[5] or 0)}
                for row in response.get("data", [])
            ]

        return await asyncio.to_thread(fetch)


def create_market_data(settings: Settings) -> DemoMarketData | AngelOneMarketData:
    return AngelOneMarketData(settings) if settings.smartapi_ready else DemoMarketData()

