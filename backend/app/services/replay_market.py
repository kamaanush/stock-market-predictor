from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CandleHistory
from .candle_history import load_candles


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _resample_1m_to_5m(
    candles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not candles:
        return []

    buckets: dict[int, list[dict[str, Any]]] = {}

    for candle in candles:
        raw_time = candle.get("time")
        try:
            timestamp = int(float(raw_time))
        except (TypeError, ValueError):
            continue

        bucket = timestamp - (timestamp % 300)
        buckets.setdefault(bucket, []).append(candle)

    output: list[dict[str, Any]] = []

    for bucket in sorted(buckets):
        rows = sorted(
            buckets[bucket],
            key=lambda item: int(float(item.get("time", 0))),
        )

        if not rows:
            continue

        output.append(
            {
                "time": bucket,
                "open": _safe_float(rows[0].get("open")),
                "high": max(_safe_float(row.get("high")) for row in rows),
                "low": min(_safe_float(row.get("low")) for row in rows),
                "close": _safe_float(rows[-1].get("close")),
                "volume": sum(_safe_float(row.get("volume")) for row in rows),
            }
        )

    return output


class ReplayCandleEngine:
    def __init__(
        self,
        data: dict[str, dict[str, list[dict[str, Any]]]],
    ) -> None:
        self._data = data

    def candles(
        self,
        symbol: str,
        interval: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        normalized = str(symbol).strip().upper()
        rows = list(
            self._data
            .get(normalized, {})
            .get(interval, [])
        )

        if limit is not None:
            rows = rows[-limit:]

        return rows


async def stored_1m_symbols(
    session: AsyncSession,
    *,
    limit: int = 500,
) -> list[str]:
    statement = (
        select(CandleHistory.symbol)
        .where(CandleHistory.interval == "1m")
        .distinct()
        .limit(max(int(limit), 1))
    )

    result = await session.execute(statement)

    return [
        str(symbol).strip().upper()
        for symbol in result.scalars()
        if symbol
    ]


async def build_replay_inputs(
    session: AsyncSession,
    *,
    symbols: list[str] | None = None,
    symbol_limit: int = 500,
    candle_limit: int = 120,
    benchmark_symbol: str = "NIFTY 50",
) -> tuple[list[dict[str, Any]], ReplayCandleEngine]:
    if symbols is None:
        symbols = await stored_1m_symbols(
            session,
            limit=symbol_limit,
        )

    normalized_symbols: list[str] = []

    for symbol in [*symbols, benchmark_symbol]:
        normalized = str(symbol).strip().upper()

        if normalized and normalized not in normalized_symbols:
            normalized_symbols.append(normalized)

    data: dict[str, dict[str, list[dict[str, Any]]]] = {}
    ticks: list[dict[str, Any]] = []

    for symbol in normalized_symbols:
        one_minute = await load_candles(
            session,
            symbol=symbol,
            interval="1m",
            limit=max(int(candle_limit), 12),
        )

        if not one_minute:
            continue

        latest_time = int(float(one_minute[-1].get("time", 0)))
        cutoff = latest_time - (12 * 60 * 60)

        latest_session = [
            candle
            for candle in one_minute
            if int(float(candle.get("time", 0))) >= cutoff
        ]

        if not latest_session:
            continue

        five_minute = _resample_1m_to_5m(latest_session)

        data[symbol] = {
            "1m": latest_session,
            "5m": five_minute,
        }

        if symbol == benchmark_symbol.upper():
            continue

        latest = latest_session[-1]

        ticks.append(
            {
                "symbol": symbol,
                "ltp": _safe_float(latest.get("close")),
                "volume": _safe_float(latest.get("volume")),
                "exchange_timestamp": latest.get("time"),
                "source": "REPLAY",
            }
        )

    return ticks, ReplayCandleEngine(data)
