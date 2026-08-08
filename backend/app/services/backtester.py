from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .pipeline_service import build_pipeline_analysis
from .scanner import scan_symbol


@dataclass(frozen=True)
class BacktestTrade:
    symbol: str
    timeframe: str
    signal: str
    confidence: int
    grade: str

    entry: float
    stoploss: float
    target1: float
    target2: float

    entry_index: int
    exit_index: int | None
    exit_price: float | None

    result: str
    r_multiple: float
    bars_held: int

    target1_reached: bool


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    timeframe: str

    candles: int
    setups: int
    triggered: int

    wins: int
    losses: int
    breakeven: int

    unresolved: int
    not_triggered: int

    target1_hits: int
    target2_hits: int
    stoploss_hits: int

    win_rate: float
    average_r: float
    total_r: float
    profit_factor: float | None

    trades: tuple[BacktestTrade, ...]


def _get_master_confidence(
    pipeline: dict[str, Any],
) -> int:
    confidence_data = pipeline.get(
        "confidence",
        {},
    )

    return int(
        confidence_data.get(
            "confidence",
            0,
        )
    )


def _get_master_grade(
    pipeline: dict[str, Any],
) -> str:
    confidence_data = pipeline.get(
        "confidence",
        {},
    )

    return str(
        confidence_data.get(
            "grade",
            "AVOID",
        )
    )


def _get_signal(
    pipeline: dict[str, Any],
) -> str:
    decision = pipeline.get(
        "decision",
        {},
    )

    return str(
        decision.get(
            "signal",
            "WAIT",
        )
    ).upper()


def _extract_trade_plan(
    scanner_result: dict[str, Any],
) -> tuple[
    float | None,
    float | None,
    float | None,
    float | None,
]:
    entry = scanner_result.get(
        "entry_price"
    )

    stoploss = scanner_result.get(
        "stoploss"
    )

    target1 = scanner_result.get(
        "target1"
    )

    target2 = scanner_result.get(
        "target2"
    )

    if (
        entry is None
        or stoploss is None
        or target1 is None
        or target2 is None
    ):
        return (
            None,
            None,
            None,
            None,
        )

    return (
        float(entry),
        float(stoploss),
        float(target1),
        float(target2),
    )


def _make_trade(
    *,
    symbol: str,
    timeframe: str,
    signal: str,
    confidence: int,
    grade: str,
    entry: float,
    stoploss: float,
    target1: float,
    target2: float,
    entry_index: int,
    exit_index: int | None,
    exit_price: float | None,
    result: str,
    r_multiple: float,
    bars_held: int,
    target1_reached: bool,
) -> BacktestTrade:
    return BacktestTrade(
        symbol=symbol,
        timeframe=timeframe,
        signal=signal,
        confidence=confidence,
        grade=grade,
        entry=entry,
        stoploss=stoploss,
        target1=target1,
        target2=target2,
        entry_index=entry_index,
        exit_index=exit_index,
        exit_price=exit_price,
        result=result,
        r_multiple=round(
            r_multiple,
            3,
        ),
        bars_held=bars_held,
        target1_reached=(
            target1_reached
        ),
    )


def _evaluate_trade(
    *,
    symbol: str,
    timeframe: str,
    signal: str,
    confidence: int,
    grade: str,
    entry: float,
    stoploss: float,
    target1: float,
    target2: float,
    entry_index: int,
    future_candles: list[
        dict[str, Any]
    ],
    max_hold_bars: int,
) -> BacktestTrade:

    risk_amount = abs(
        entry - stoploss
    )

    if risk_amount <= 0:
        return _make_trade(
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            grade=grade,
            entry=entry,
            stoploss=stoploss,
            target1=target1,
            target2=target2,
            entry_index=entry_index,
            exit_index=None,
            exit_price=None,
            result="INVALID",
            r_multiple=0.0,
            bars_held=0,
            target1_reached=False,
        )

    candles_to_check = (
        future_candles[
            :max_hold_bars
        ]
    )

    trade_active = False
    target1_reached = False

    active_stop = stoploss

    for offset, candle in enumerate(
        candles_to_check,
        start=1,
    ):
        high = float(
            candle["high"]
        )

        low = float(
            candle["low"]
        )

        # =============================================
        # BUY
        # =============================================

        if signal == "BUY":

            if not trade_active:
                if high < entry:
                    continue

                trade_active = True

            # -----------------------------------------
            # BEFORE TARGET 1
            # -----------------------------------------

            if not target1_reached:

                # Conservative OHLC assumption.
                #
                # If both SL and target occur within
                # the same candle, SL is evaluated
                # first.

                if low <= active_stop:
                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=(
                            stoploss
                        ),
                        result="STOPLOSS",
                        r_multiple=-1.0,
                        bars_held=offset,
                        target1_reached=False,
                    )

                if high >= target2:
                    reward = (
                        target2
                        - entry
                    )

                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=(
                            reward
                            / risk_amount
                        ),
                        bars_held=offset,
                        target1_reached=True,
                    )

                if high >= target1:
                    target1_reached = True

                    # Once T1 is reached,
                    # protect the position at entry.
                    active_stop = entry

                    continue

            # -----------------------------------------
            # AFTER TARGET 1
            # -----------------------------------------

            else:

                if low <= active_stop:
                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=entry,
                        result="BREAKEVEN",
                        r_multiple=0.0,
                        bars_held=offset,
                        target1_reached=True,
                    )

                if high >= target2:
                    reward = (
                        target2
                        - entry
                    )

                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=(
                            reward
                            / risk_amount
                        ),
                        bars_held=offset,
                        target1_reached=True,
                    )

        # =============================================
        # SELL
        # =============================================

        elif signal == "SELL":

            if not trade_active:
                if low > entry:
                    continue

                trade_active = True

            # -----------------------------------------
            # BEFORE TARGET 1
            # -----------------------------------------

            if not target1_reached:

                if high >= active_stop:
                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=(
                            stoploss
                        ),
                        result="STOPLOSS",
                        r_multiple=-1.0,
                        bars_held=offset,
                        target1_reached=False,
                    )

                if low <= target2:
                    reward = (
                        entry
                        - target2
                    )

                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=(
                            reward
                            / risk_amount
                        ),
                        bars_held=offset,
                        target1_reached=True,
                    )

                if low <= target1:
                    target1_reached = True

                    active_stop = entry

                    continue

            # -----------------------------------------
            # AFTER TARGET 1
            # -----------------------------------------

            else:

                if high >= active_stop:
                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=entry,
                        result="BREAKEVEN",
                        r_multiple=0.0,
                        bars_held=offset,
                        target1_reached=True,
                    )

                if low <= target2:
                    reward = (
                        entry
                        - target2
                    )

                    return _make_trade(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal=signal,
                        confidence=confidence,
                        grade=grade,
                        entry=entry,
                        stoploss=stoploss,
                        target1=target1,
                        target2=target2,
                        entry_index=(
                            entry_index
                        ),
                        exit_index=(
                            entry_index
                            + offset
                        ),
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=(
                            reward
                            / risk_amount
                        ),
                        bars_held=offset,
                        target1_reached=True,
                    )

    # =============================================
    # ENTRY NEVER TRIGGERED
    # =============================================

    if not trade_active:
        return _make_trade(
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            grade=grade,
            entry=entry,
            stoploss=stoploss,
            target1=target1,
            target2=target2,
            entry_index=entry_index,
            exit_index=None,
            exit_price=None,
            result="NOT_TRIGGERED",
            r_multiple=0.0,
            bars_held=len(
                candles_to_check
            ),
            target1_reached=False,
        )

    # =============================================
    # TARGET 1 REACHED, T2 NOT REACHED
    # =============================================

    if target1_reached:
        reward = abs(
            target1
            - entry
        )

        return _make_trade(
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            grade=grade,
            entry=entry,
            stoploss=stoploss,
            target1=target1,
            target2=target2,
            entry_index=entry_index,
            exit_index=(
                entry_index
                + len(
                    candles_to_check
                )
            ),
            exit_price=target1,
            result="TARGET1",
            r_multiple=(
                reward
                / risk_amount
            ),
            bars_held=len(
                candles_to_check
            ),
            target1_reached=True,
        )

    # =============================================
    # ACTIVE BUT UNRESOLVED
    # =============================================

    return _make_trade(
        symbol=symbol,
        timeframe=timeframe,
        signal=signal,
        confidence=confidence,
        grade=grade,
        entry=entry,
        stoploss=stoploss,
        target1=target1,
        target2=target2,
        entry_index=entry_index,
        exit_index=(
            entry_index
            + len(
                candles_to_check
            )
        ),
        exit_price=None,
        result="UNRESOLVED",
        r_multiple=0.0,
        bars_held=len(
            candles_to_check
        ),
        target1_reached=False,
    )


def run_backtest(
    *,
    symbol: str,
    timeframe: str,
    candles: list[
        dict[str, Any]
    ],
    minimum_confidence: int = 60,
    warmup_bars: int = 60,
    max_hold_bars: int = 12,
) -> BacktestResult:

    if timeframe not in {
        "1m",
        "5m",
        "15m",
    }:
        raise ValueError(
            "Backtest timeframe must be "
            "1m, 5m, or 15m"
        )

    if len(candles) <= warmup_bars:
        raise ValueError(
            "Not enough candles for backtest"
        )

    if max_hold_bars < 1:
        raise ValueError(
            "max_hold_bars must be at least 1"
        )

    trades: list[
        BacktestTrade
    ] = []

    setups = 0

    final_index = (
        len(candles)
        - max_hold_bars
    )

    # Prevent duplicate/overlapping trades.
    blocked_until_index = -1

    for index in range(
        warmup_bars,
        final_index,
    ):

        if index <= blocked_until_index:
            continue

        # =============================================
        # LOOK-AHEAD PROTECTION
        # =============================================

        historical_candles = (
            candles[
                :index + 1
            ]
        )

        scanner_result = (
            scan_symbol(
                symbol=symbol,
                candles=(
                    historical_candles
                ),
            )
        )

        pipeline = (
            build_pipeline_analysis(
                result=scanner_result,
                candles=(
                    historical_candles
                ),
            )
        )

        signal = _get_signal(
            pipeline
        )

        if signal not in {
            "BUY",
            "SELL",
        }:
            continue

        setups += 1

        confidence = (
            _get_master_confidence(
                pipeline
            )
        )

        if (
            confidence
            < minimum_confidence
        ):
            continue

        grade = (
            _get_master_grade(
                pipeline
            )
        )

        (
            entry,
            stoploss,
            target1,
            target2,
        ) = _extract_trade_plan(
            scanner_result
        )

        if (
            entry is None
            or stoploss is None
            or target1 is None
            or target2 is None
        ):
            continue

        future_candles = (
            candles[
                index + 1:
            ]
        )

        trade = _evaluate_trade(
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            grade=grade,
            entry=entry,
            stoploss=stoploss,
            target1=target1,
            target2=target2,
            entry_index=index,
            future_candles=(
                future_candles
            ),
            max_hold_bars=(
                max_hold_bars
            ),
        )

        trades.append(
            trade
        )

        # =============================================
        # OVERLAP PROTECTION
        # =============================================

        if trade.exit_index is not None:
            blocked_until_index = (
                trade.exit_index
            )

        else:
            blocked_until_index = (
                index
                + max_hold_bars
            )

    # =============================================
    # STATISTICS
    # =============================================

    target1_hits = sum(
        1
        for trade in trades
        if trade.result
        == "TARGET1"
    )

    target2_hits = sum(
        1
        for trade in trades
        if trade.result
        == "TARGET2"
    )

    stoploss_hits = sum(
        1
        for trade in trades
        if trade.result
        == "STOPLOSS"
    )

    breakeven = sum(
        1
        for trade in trades
        if trade.result
        == "BREAKEVEN"
    )

    unresolved = sum(
        1
        for trade in trades
        if trade.result
        == "UNRESOLVED"
    )

    not_triggered = sum(
        1
        for trade in trades
        if trade.result
        == "NOT_TRIGGERED"
    )

    wins = (
        target1_hits
        + target2_hits
    )

    losses = (
        stoploss_hits
    )

    resolved_directional = (
        wins
        + losses
    )

    win_rate = (
        round(
            (
                wins
                / resolved_directional
            )
            * 100,
            2,
        )
        if resolved_directional
        else 0.0
    )

    executed_trades = [
        trade
        for trade in trades
        if trade.result
        not in {
            "NOT_TRIGGERED",
            "INVALID",
        }
    ]

    total_r = round(
        sum(
            trade.r_multiple
            for trade
            in executed_trades
        ),
        3,
    )

    average_r = (
        round(
            total_r
            / len(
                executed_trades
            ),
            3,
        )
        if executed_trades
        else 0.0
    )

    gross_profit = sum(
        trade.r_multiple
        for trade
        in executed_trades
        if trade.r_multiple > 0
    )

    gross_loss = abs(
        sum(
            trade.r_multiple
            for trade
            in executed_trades
            if trade.r_multiple < 0
        )
    )

    if gross_loss > 0:
        profit_factor = round(
            gross_profit
            / gross_loss,
            3,
        )

    elif gross_profit > 0:
        # No losing trades.
        profit_factor = None

    else:
        profit_factor = None

    triggered = sum(
        1
        for trade in trades
        if trade.result
        not in {
            "NOT_TRIGGERED",
            "INVALID",
        }
    )

    return BacktestResult(
        symbol=symbol.upper(),
        timeframe=timeframe,

        candles=len(
            candles
        ),

        setups=setups,

        triggered=triggered,

        wins=wins,
        losses=losses,

        breakeven=breakeven,

        unresolved=unresolved,

        not_triggered=(
            not_triggered
        ),

        target1_hits=(
            target1_hits
        ),

        target2_hits=(
            target2_hits
        ),

        stoploss_hits=(
            stoploss_hits
        ),

        win_rate=win_rate,

        average_r=average_r,

        total_r=total_r,

        profit_factor=(
            profit_factor
        ),

        trades=tuple(
            trades
        ),
    )


def backtest_to_dict(
    result: BacktestResult,
) -> dict[str, Any]:
    return asdict(
        result
    )