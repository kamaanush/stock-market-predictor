from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Awaitable, Callable, Iterable, Optional

from .market_scanner import (
    MarketOpportunity,
    rank_opportunities,
)
from .multi_timeframe import (
    MultiTimeframeResult,
    evaluate_multi_timeframe,
)
from .pipeline_service import build_pipeline_analysis
from .scanner import scan_symbol


SUPPORTED_TIMEFRAMES = (
    "1m",
    "5m",
    "15m",
)


@dataclass(frozen=True)
class ScanInstrument:
    symbol: str
    token: Optional[str] = None
    name: Optional[str] = None


@dataclass(frozen=True)
class SymbolScanResult:
    symbol: str
    name: Optional[str]
    signal: str
    confidence: int
    grade: str
    action: str
    alignment: str
    strongest_timeframe: str
    timeframes: dict[str, Any]


@dataclass(frozen=True)
class SymbolScanFailure:
    symbol: str
    error: str


@dataclass(frozen=True)
class MarketScanResult:
    scanned: int
    successful: int
    failed: int
    opportunities: tuple[SymbolScanResult, ...]
    failures: tuple[SymbolScanFailure, ...]


CandleFetcher = Callable[
    [
        str,
        str,
        Optional[str],
    ],
    Awaitable[list[dict[str, Any]]],
]


def confidence_to_grade(
    confidence: int,
) -> str:
    if confidence >= 92:
        return "A+"

    if confidence >= 84:
        return "A"

    if confidence >= 74:
        return "B"

    if confidence >= 62:
        return "C"

    return "AVOID"


def determine_action(
    *,
    multi_timeframe: MultiTimeframeResult,
    timeframe_results: dict[str, dict[str, Any]],
) -> str:
    if multi_timeframe.signal == "WAIT":
        return "NO TRADE"

    preferred_timeframe = (
        "5m"
        if "5m" in timeframe_results
        else multi_timeframe.strongest_timeframe
    )

    preferred = timeframe_results.get(
        preferred_timeframe,
        {},
    )

    decision = preferred.get(
        "decision",
        {},
    )

    action = str(
        decision.get(
            "action",
            "NO TRADE",
        )
    ).upper()

    if (
        multi_timeframe.signal == "BUY"
        and action == "WAIT BREAKOUT"
    ):
        return "WAIT BREAKOUT"

    if (
        multi_timeframe.signal == "SELL"
        and action == "WAIT BREAKDOWN"
    ):
        return "WAIT BREAKDOWN"

    if action == "ACTIVE":
        return "ACTIVE"

    return action


async def scan_single_timeframe(
    *,
    instrument: ScanInstrument,
    timeframe: str,
    fetch_candles: CandleFetcher,
) -> dict[str, Any]:
    candles = await fetch_candles(
        instrument.symbol,
        timeframe,
        instrument.token,
    )

    scanner_result = scan_symbol(
        symbol=instrument.symbol,
        candles=candles,
    )

    pipeline_result = build_pipeline_analysis(
        result=scanner_result,
        candles=candles,
    )

    return {
        **pipeline_result,
        "scanner": scanner_result,
    }


async def scan_single_symbol(
    *,
    instrument: ScanInstrument,
    fetch_candles: CandleFetcher,
) -> SymbolScanResult:
    timeframe_results: dict[
        str,
        dict[str, Any],
    ] = {}

    for timeframe in SUPPORTED_TIMEFRAMES:
        timeframe_results[
            timeframe
        ] = await scan_single_timeframe(
            instrument=instrument,
            timeframe=timeframe,
            fetch_candles=fetch_candles,
        )

    multi_timeframe = evaluate_multi_timeframe(
        timeframe_results
    )

    action = determine_action(
        multi_timeframe=multi_timeframe,
        timeframe_results=timeframe_results,
    )

    grade = confidence_to_grade(
        multi_timeframe.confidence
    )

    compact_timeframes: dict[
        str,
        Any,
    ] = {}

    for timeframe, result in (
        timeframe_results.items()
    ):
        compact_timeframes[timeframe] = {
            "decision": result.get(
                "decision",
                {},
            ),

            "market_structure": result.get(
                "market_structure",
                {},
            ),

            "trend_strength": result.get(
                "trend_strength",
                {},
            ),

            "momentum": result.get(
                "momentum",
                {},
            ),

            "participation": result.get(
                "participation",
                {},
            ),

            "buyer_seller_pressure": result.get(
                "buyer_seller_pressure",
                {},
            ),

            "candle_flow": result.get(
                "candle_flow",
                {},
            ),

            "location": result.get(
                "location",
                {},
            ),

            "risk": result.get(
                "risk",
                {},
            ),

            "breakout_readiness": result.get(
                "breakout_readiness",
                {},
            ),

            "confidence": result.get(
                "confidence",
                {},
            ),
        }

    return SymbolScanResult(
        symbol=instrument.symbol.upper(),
        name=instrument.name,
        signal=multi_timeframe.signal,
        confidence=(
            multi_timeframe.confidence
        ),
        grade=grade,
        action=action,
        alignment=multi_timeframe.alignment,
        strongest_timeframe=(
            multi_timeframe.strongest_timeframe
        ),
        timeframes=compact_timeframes,
    )


async def run_market_scan(
    *,
    instruments: Iterable[ScanInstrument],
    fetch_candles: CandleFetcher,
    concurrency: int = 4,
) -> MarketScanResult:
    instrument_list = list(instruments)

    if not instrument_list:
        return MarketScanResult(
            scanned=0,
            successful=0,
            failed=0,
            opportunities=(),
            failures=(),
        )

    semaphore = asyncio.Semaphore(
        max(1, concurrency)
    )

    async def protected_scan(
        instrument: ScanInstrument,
    ) -> tuple[
        Optional[SymbolScanResult],
        Optional[SymbolScanFailure],
    ]:
        async with semaphore:
            try:
                result = await scan_single_symbol(
                    instrument=instrument,
                    fetch_candles=fetch_candles,
                )

                return result, None

            except Exception as exc:
                return (
                    None,
                    SymbolScanFailure(
                        symbol=(
                            instrument.symbol.upper()
                        ),
                        error=str(exc),
                    ),
                )

    raw_results = await asyncio.gather(
        *[
            protected_scan(instrument)
            for instrument in instrument_list
        ]
    )

    successful_results: list[
        SymbolScanResult
    ] = []

    failures: list[
        SymbolScanFailure
    ] = []

    for result, failure in raw_results:
        if result is not None:
            successful_results.append(result)

        if failure is not None:
            failures.append(failure)

    ranking_items = [
        MarketOpportunity(
            symbol=item.symbol,
            signal=item.signal,
            confidence=item.confidence,
            grade=item.grade,
            action=item.action,
        )
        for item in successful_results
    ]

    ranked = rank_opportunities(
        ranking_items
    )

    ranking_positions = {
        item.symbol: index
        for index, item in enumerate(
            ranked
        )
    }

    successful_results.sort(
        key=lambda item: ranking_positions.get(
            item.symbol,
            999999,
        )
    )

    return MarketScanResult(
        scanned=len(instrument_list),
        successful=len(
            successful_results
        ),
        failed=len(failures),
        opportunities=tuple(
            successful_results
        ),
        failures=tuple(failures),
    )


def market_scan_to_dict(
    result: MarketScanResult,
) -> dict[str, Any]:
    return asdict(result)