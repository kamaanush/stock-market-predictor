from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Any, Optional

from .pipeline_service import build_pipeline_analysis
from .scanner import (
    prepare_scanner_dataframe,
    scan_symbol_from_dataframe,
)


DEFAULT_INITIAL_CAPITAL = 100000.0
DEFAULT_RISK_PER_TRADE_PCT = 1.0
DEFAULT_MAX_POSITION_VALUE_PCT = 100.0
DEFAULT_SLIPPAGE_BPS = 5.0

# Estimated NSE equity-intraday charges. Keep these configurable because
# broker/exchange/regulatory charges can change over time.
BROKERAGE_RATE = 0.0003
BROKERAGE_CAP_PER_ORDER = 20.0
STT_SELL_RATE = 0.00025
EXCHANGE_TRANSACTION_RATE = 0.0000297
SEBI_TURNOVER_RATE = 0.000001
STAMP_DUTY_BUY_RATE = 0.00003
GST_RATE = 0.18


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
    exit_index: Optional[int]
    exit_price: Optional[float]

    result: str
    r_multiple: float
    bars_held: int
    target1_reached: bool

    quantity: int = 0
    executed_entry: float = 0.0
    executed_exit: Optional[float] = None
    gross_pnl: float = 0.0
    charges: float = 0.0
    net_pnl: float = 0.0


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
    executed_win_rate: float
    average_r: float
    total_r: float
    profit_factor: Optional[float]
    net_profit_factor: Optional[float]

    initial_capital: float
    ending_capital: float
    gross_pnl: float
    total_charges: float
    net_pnl: float
    net_return_percent: float

    expectancy: float
    average_winner: float
    average_loser: float

    max_drawdown: float
    max_drawdown_percent: float
    longest_winning_streak: int
    longest_losing_streak: int

    slippage_bps: float
    risk_per_trade_percent: float
    max_position_value_percent: float

    equity_curve: tuple[dict[str, Any], ...]
    monthly_returns: tuple[dict[str, Any], ...]
    trades: tuple[BacktestTrade, ...]


def _get_master_confidence(pipeline: dict[str, Any]) -> int:
    confidence_data = pipeline.get("confidence", {})
    return int(confidence_data.get("confidence", 0))


def _get_master_grade(pipeline: dict[str, Any]) -> str:
    confidence_data = pipeline.get("confidence", {})
    return str(confidence_data.get("grade", "AVOID"))


def _get_signal(pipeline: dict[str, Any]) -> str:
    decision = pipeline.get("decision", {})
    return str(decision.get("signal", "WAIT")).upper()


def _extract_trade_plan(
    scanner_result: dict[str, Any],
) -> tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
]:
    entry = scanner_result.get("entry_price")
    stoploss = scanner_result.get("stoploss")
    target1 = scanner_result.get("target1")
    target2 = scanner_result.get("target2")

    if entry is None or stoploss is None or target1 is None or target2 is None:
        return None, None, None, None

    return float(entry), float(stoploss), float(target1), float(target2)


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
    exit_index: Optional[int],
    exit_price: Optional[float],
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
        r_multiple=round(r_multiple, 3),
        bars_held=bars_held,
        target1_reached=target1_reached,
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
    future_candles: list[dict[str, Any]],
    max_hold_bars: int,
) -> BacktestTrade:
    risk_amount = abs(entry - stoploss)

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

    candles_to_check = future_candles[:max_hold_bars]
    trade_active = False
    target1_reached = False
    active_stop = stoploss

    for offset, candle in enumerate(candles_to_check, start=1):
        high = float(candle["high"])
        low = float(candle["low"])

        if signal == "BUY":
            if not trade_active:
                if high < entry:
                    continue
                trade_active = True

            if not target1_reached:
                # Conservative OHLC assumption: if SL and target are touched
                # in the same candle, the stop is evaluated first.
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
                        entry_index=entry_index,
                        exit_index=entry_index + offset,
                        exit_price=stoploss,
                        result="STOPLOSS",
                        r_multiple=-1.0,
                        bars_held=offset,
                        target1_reached=False,
                    )

                if high >= target2:
                    reward = target2 - entry
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
                        exit_index=entry_index + offset,
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=reward / risk_amount,
                        bars_held=offset,
                        target1_reached=True,
                    )

                if high >= target1:
                    target1_reached = True
                    active_stop = entry
                    continue

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
                        entry_index=entry_index,
                        exit_index=entry_index + offset,
                        exit_price=entry,
                        result="BREAKEVEN",
                        r_multiple=0.0,
                        bars_held=offset,
                        target1_reached=True,
                    )

                if high >= target2:
                    reward = target2 - entry
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
                        exit_index=entry_index + offset,
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=reward / risk_amount,
                        bars_held=offset,
                        target1_reached=True,
                    )

        elif signal == "SELL":
            if not trade_active:
                if low > entry:
                    continue
                trade_active = True

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
                        entry_index=entry_index,
                        exit_index=entry_index + offset,
                        exit_price=stoploss,
                        result="STOPLOSS",
                        r_multiple=-1.0,
                        bars_held=offset,
                        target1_reached=False,
                    )

                if low <= target2:
                    reward = entry - target2
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
                        exit_index=entry_index + offset,
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=reward / risk_amount,
                        bars_held=offset,
                        target1_reached=True,
                    )

                if low <= target1:
                    target1_reached = True
                    active_stop = entry
                    continue

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
                        entry_index=entry_index,
                        exit_index=entry_index + offset,
                        exit_price=entry,
                        result="BREAKEVEN",
                        r_multiple=0.0,
                        bars_held=offset,
                        target1_reached=True,
                    )

                if low <= target2:
                    reward = entry - target2
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
                        exit_index=entry_index + offset,
                        exit_price=target2,
                        result="TARGET2",
                        r_multiple=reward / risk_amount,
                        bars_held=offset,
                        target1_reached=True,
                    )

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
            bars_held=len(candles_to_check),
            target1_reached=False,
        )

    final_close = float(candles_to_check[-1]["close"])

    if signal == "BUY":
        mark_to_market_r = (final_close - entry) / risk_amount
    elif signal == "SELL":
        mark_to_market_r = (entry - final_close) / risk_amount
    else:
        mark_to_market_r = 0.0

    if target1_reached:
        # T1 was reached during the holding window, but T2 and the
        # breakeven stop were not reached afterward. Exit at the final
        # candle close instead of assuming the full position can still
        # be closed at T1. This is more conservative and market-realistic.
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
            exit_index=entry_index + len(candles_to_check),
            exit_price=final_close,
            result="TARGET1",
            r_multiple=mark_to_market_r,
            bars_held=len(candles_to_check),
            target1_reached=True,
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
        exit_index=entry_index + len(candles_to_check),
        exit_price=final_close,
        result="UNRESOLVED",
        r_multiple=mark_to_market_r,
        bars_held=len(candles_to_check),
        target1_reached=False,
    )


def _apply_slippage(price: float, *, signal: str, side: str, slippage_bps: float) -> float:
    slip = max(0.0, slippage_bps) / 10000.0

    if signal == "BUY":
        multiplier = 1.0 + slip if side == "ENTRY" else 1.0 - slip
    else:
        multiplier = 1.0 - slip if side == "ENTRY" else 1.0 + slip

    return price * multiplier


def _estimate_intraday_charges(
    *,
    signal: str,
    entry_price: float,
    exit_price: float,
    quantity: int,
) -> float:
    if quantity <= 0:
        return 0.0

    entry_turnover = abs(entry_price * quantity)
    exit_turnover = abs(exit_price * quantity)
    total_turnover = entry_turnover + exit_turnover

    entry_brokerage = min(BROKERAGE_CAP_PER_ORDER, entry_turnover * BROKERAGE_RATE)
    exit_brokerage = min(BROKERAGE_CAP_PER_ORDER, exit_turnover * BROKERAGE_RATE)
    brokerage = entry_brokerage + exit_brokerage

    if signal == "BUY":
        sell_turnover = exit_turnover
        buy_turnover = entry_turnover
    else:
        sell_turnover = entry_turnover
        buy_turnover = exit_turnover

    stt = sell_turnover * STT_SELL_RATE
    exchange_charge = total_turnover * EXCHANGE_TRANSACTION_RATE
    sebi_charge = total_turnover * SEBI_TURNOVER_RATE
    stamp_duty = buy_turnover * STAMP_DUTY_BUY_RATE
    gst = (brokerage + exchange_charge + sebi_charge) * GST_RATE

    return round(
        brokerage + stt + exchange_charge + sebi_charge + stamp_duty + gst,
        2,
    )


def _apply_trade_financials(
    trade: BacktestTrade,
    *,
    available_equity: float,
    risk_per_trade_pct: float,
    max_position_value_pct: float,
    slippage_bps: float,
) -> BacktestTrade:
    if trade.result in {"NOT_TRIGGERED", "INVALID"} or trade.exit_price is None:
        return trade

    planned_risk_per_share = abs(trade.entry - trade.stoploss)
    if planned_risk_per_share <= 0 or available_equity <= 0:
        return trade

    executed_entry = _apply_slippage(
        trade.entry,
        signal=trade.signal,
        side="ENTRY",
        slippage_bps=slippage_bps,
    )
    executed_exit = _apply_slippage(
        float(trade.exit_price),
        signal=trade.signal,
        side="EXIT",
        slippage_bps=slippage_bps,
    )

    risk_budget = available_equity * max(0.0, risk_per_trade_pct) / 100.0
    max_position_value = (
        available_equity * max(0.0, max_position_value_pct) / 100.0
    )

    risk_quantity = int(risk_budget / planned_risk_per_share)
    value_quantity = int(max_position_value / max(executed_entry, 0.000001))
    quantity = max(0, min(risk_quantity, value_quantity))

    if quantity <= 0:
        return replace(
            trade,
            executed_entry=round(executed_entry, 4),
            executed_exit=round(executed_exit, 4),
        )

    if trade.signal == "BUY":
        gross_pnl = (executed_exit - executed_entry) * quantity
    else:
        gross_pnl = (executed_entry - executed_exit) * quantity

    charges = _estimate_intraday_charges(
        signal=trade.signal,
        entry_price=executed_entry,
        exit_price=executed_exit,
        quantity=quantity,
    )
    net_pnl = gross_pnl - charges

    return replace(
        trade,
        quantity=quantity,
        executed_entry=round(executed_entry, 4),
        executed_exit=round(executed_exit, 4),
        gross_pnl=round(gross_pnl, 2),
        charges=round(charges, 2),
        net_pnl=round(net_pnl, 2),
    )


def _candle_time_value(candles: list[dict[str, Any]], index: Optional[int]) -> Any:
    if index is None or index < 0 or index >= len(candles):
        return None

    candle = candles[index]
    return candle.get("time", candle.get("timestamp"))


def _month_key(value: Any) -> str:
    if value is None:
        return "UNKNOWN"

    try:
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 100000000000:
                timestamp /= 1000.0
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m")

        text = str(value).strip()
        if text.isdigit():
            timestamp = float(text)
            if timestamp > 100000000000:
                timestamp /= 1000.0
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m")

        normalized = text.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).strftime("%Y-%m")
    except (ValueError, TypeError, OSError, OverflowError):
        return "UNKNOWN"


def _build_financial_statistics(
    *,
    trades: list[BacktestTrade],
    candles: list[dict[str, Any]],
    initial_capital: float,
) -> dict[str, Any]:
    executed = [
        trade
        for trade in trades
        if trade.result not in {"NOT_TRIGGERED", "INVALID"}
    ]

    gross_pnl = round(sum(trade.gross_pnl for trade in executed), 2)
    total_charges = round(sum(trade.charges for trade in executed), 2)
    net_pnl = round(sum(trade.net_pnl for trade in executed), 2)
    ending_capital = round(initial_capital + net_pnl, 2)
    net_return_percent = (
        round((net_pnl / initial_capital) * 100.0, 2)
        if initial_capital > 0
        else 0.0
    )

    positive_net = [trade.net_pnl for trade in executed if trade.net_pnl > 0]
    negative_net = [trade.net_pnl for trade in executed if trade.net_pnl < 0]

    expectancy = round(net_pnl / len(executed), 2) if executed else 0.0
    average_winner = (
        round(sum(positive_net) / len(positive_net), 2) if positive_net else 0.0
    )
    average_loser = (
        round(sum(negative_net) / len(negative_net), 2) if negative_net else 0.0
    )

    gross_net_profit = sum(positive_net)
    gross_net_loss = abs(sum(negative_net))
    if gross_net_loss > 0:
        net_profit_factor: Optional[float] = round(
            gross_net_profit / gross_net_loss,
            3,
        )
    else:
        net_profit_factor = None

    equity = float(initial_capital)
    peak = float(initial_capital)
    max_drawdown = 0.0
    max_drawdown_percent = 0.0
    equity_curve: list[dict[str, Any]] = []

    current_win_streak = 0
    current_loss_streak = 0
    longest_winning_streak = 0
    longest_losing_streak = 0

    monthly: dict[str, dict[str, Any]] = {}

    for trade_number, trade in enumerate(executed, start=1):
        equity_before = equity
        equity += trade.net_pnl
        peak = max(peak, equity)

        drawdown = max(0.0, peak - equity)
        drawdown_percent = (drawdown / peak) * 100.0 if peak > 0 else 0.0

        max_drawdown = max(max_drawdown, drawdown)
        max_drawdown_percent = max(max_drawdown_percent, drawdown_percent)

        if trade.net_pnl > 0:
            current_win_streak += 1
            current_loss_streak = 0
            longest_winning_streak = max(
                longest_winning_streak,
                current_win_streak,
            )
        elif trade.net_pnl < 0:
            current_loss_streak += 1
            current_win_streak = 0
            longest_losing_streak = max(
                longest_losing_streak,
                current_loss_streak,
            )
        else:
            current_win_streak = 0
            current_loss_streak = 0

        exit_time = _candle_time_value(candles, trade.exit_index)
        month = _month_key(exit_time)

        if month not in monthly:
            monthly[month] = {
                "month": month,
                "trades": 0,
                "gross_pnl": 0.0,
                "charges": 0.0,
                "net_pnl": 0.0,
                "start_equity": equity_before,
                "end_equity": equity_before,
            }

        month_row = monthly[month]
        month_row["trades"] += 1
        month_row["gross_pnl"] += trade.gross_pnl
        month_row["charges"] += trade.charges
        month_row["net_pnl"] += trade.net_pnl
        month_row["end_equity"] = equity

        equity_curve.append(
            {
                "trade_number": trade_number,
                "exit_index": trade.exit_index,
                "time": exit_time,
                "result": trade.result,
                "net_pnl": round(trade.net_pnl, 2),
                "equity": round(equity, 2),
                "drawdown": round(drawdown, 2),
                "drawdown_percent": round(drawdown_percent, 2),
            }
        )

    monthly_returns: list[dict[str, Any]] = []
    for month in sorted(monthly.keys()):
        row = monthly[month]
        start_equity = float(row["start_equity"])
        end_equity = float(row["end_equity"])
        month_return = (
            ((end_equity - start_equity) / start_equity) * 100.0
            if start_equity > 0
            else 0.0
        )

        monthly_returns.append(
            {
                "month": month,
                "trades": int(row["trades"]),
                "gross_pnl": round(float(row["gross_pnl"]), 2),
                "charges": round(float(row["charges"]), 2),
                "net_pnl": round(float(row["net_pnl"]), 2),
                "return_percent": round(month_return, 2),
                "start_equity": round(start_equity, 2),
                "end_equity": round(end_equity, 2),
            }
        )

    return {
        "gross_pnl": gross_pnl,
        "total_charges": total_charges,
        "net_pnl": net_pnl,
        "ending_capital": ending_capital,
        "net_return_percent": net_return_percent,
        "expectancy": expectancy,
        "average_winner": average_winner,
        "average_loser": average_loser,
        "net_profit_factor": net_profit_factor,
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_percent": round(max_drawdown_percent, 2),
        "longest_winning_streak": longest_winning_streak,
        "longest_losing_streak": longest_losing_streak,
        "equity_curve": tuple(equity_curve),
        "monthly_returns": tuple(monthly_returns),
    }


def run_backtest(
    *,
    symbol: str,
    timeframe: str,
    candles: list[dict[str, Any]],
    minimum_confidence: int = 60,
    warmup_bars: int = 60,
    max_hold_bars: int = 12,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    risk_per_trade_pct: float = DEFAULT_RISK_PER_TRADE_PCT,
    max_position_value_pct: float = DEFAULT_MAX_POSITION_VALUE_PCT,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> BacktestResult:
    if timeframe not in {"1m", "5m", "15m"}:
        raise ValueError("Backtest timeframe must be 1m, 5m, or 15m")

    if len(candles) <= warmup_bars:
        raise ValueError("Not enough candles for backtest")

    if max_hold_bars < 1:
        raise ValueError("max_hold_bars must be at least 1")

    if initial_capital <= 0:
        raise ValueError("initial_capital must be greater than 0")

    if risk_per_trade_pct <= 0:
        raise ValueError("risk_per_trade_pct must be greater than 0")

    if max_position_value_pct <= 0:
        raise ValueError("max_position_value_pct must be greater than 0")

    if slippage_bps < 0:
        raise ValueError("slippage_bps cannot be negative")

    prepared_dataframe = (
        prepare_scanner_dataframe(
            candles
        )
    )

    if len(prepared_dataframe) != len(candles):
        raise ValueError(
            "Historical candle cleaning changed "
            "the candle count; cannot safely "
            "preserve backtest indexes"
        )

    trades: list[BacktestTrade] = []
    setups = 0
    final_index = len(candles) - max_hold_bars
    blocked_until_index = -1
    current_equity = float(initial_capital)

    for index in range(warmup_bars, final_index):
        if index <= blocked_until_index:
            continue

        # Indicators were calculated once for speed.
        # Only the current/past row is read here.
        scanner_result = (
            scan_symbol_from_dataframe(
                symbol=symbol,
                dataframe=prepared_dataframe,
                index=index,
            )
        )

        # Preserve the exact historical candle window
        # used by the original backtester.
        historical_candles = (
            candles[: index + 1]
        )

        pipeline = build_pipeline_analysis(
            result=scanner_result,
            candles=historical_candles,
            prepared_dataframe=(
                prepared_dataframe
            ),
            prepared_index=index,
        )

        signal = _get_signal(pipeline)
        scanner_signal = str(scanner_result.get("signal", "WAIT")).upper()

        if signal not in {"BUY", "SELL"}:
            continue

        if scanner_signal not in {"BUY", "SELL"}:
            continue

        if scanner_signal != signal:
            continue

        setups += 1

        confidence = _get_master_confidence(pipeline)
        if confidence < minimum_confidence:
            continue

        grade = _get_master_grade(pipeline)
        entry, stoploss, target1, target2 = _extract_trade_plan(scanner_result)

        if entry is None or stoploss is None or target1 is None or target2 is None:
            continue

        future_candles = candles[index + 1 :]

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
            future_candles=future_candles,
            max_hold_bars=max_hold_bars,
        )

        trade = _apply_trade_financials(
            trade,
            available_equity=current_equity,
            risk_per_trade_pct=risk_per_trade_pct,
            max_position_value_pct=max_position_value_pct,
            slippage_bps=slippage_bps,
        )

        if trade.result not in {"NOT_TRIGGERED", "INVALID"}:
            current_equity += trade.net_pnl

        trades.append(trade)

        if trade.exit_index is not None:
            blocked_until_index = trade.exit_index
        else:
            blocked_until_index = index + max_hold_bars

    target1_hits = sum(1 for trade in trades if trade.result == "TARGET1")
    target2_hits = sum(1 for trade in trades if trade.result == "TARGET2")
    stoploss_hits = sum(1 for trade in trades if trade.result == "STOPLOSS")
    breakeven = sum(1 for trade in trades if trade.result == "BREAKEVEN")
    unresolved = sum(1 for trade in trades if trade.result == "UNRESOLVED")
    not_triggered = sum(1 for trade in trades if trade.result == "NOT_TRIGGERED")

    wins = target1_hits + target2_hits
    losses = stoploss_hits
    resolved_directional = wins + losses

    win_rate = (
        round((wins / resolved_directional) * 100.0, 2)
        if resolved_directional
        else 0.0
    )

    executed_trades = [
        trade
        for trade in trades
        if trade.result not in {"NOT_TRIGGERED", "INVALID"}
    ]

    triggered = len(executed_trades)
    executed_win_rate = (
        round((wins / triggered) * 100.0, 2)
        if triggered
        else 0.0
    )

    total_r = round(sum(trade.r_multiple for trade in executed_trades), 3)
    average_r = (
        round(total_r / len(executed_trades), 3)
        if executed_trades
        else 0.0
    )

    gross_profit_r = sum(
        trade.r_multiple for trade in executed_trades if trade.r_multiple > 0
    )
    gross_loss_r = abs(
        sum(trade.r_multiple for trade in executed_trades if trade.r_multiple < 0)
    )

    if gross_loss_r > 0:
        profit_factor: Optional[float] = round(gross_profit_r / gross_loss_r, 3)
    else:
        profit_factor = None

    financials = _build_financial_statistics(
        trades=trades,
        candles=candles,
        initial_capital=initial_capital,
    )

    return BacktestResult(
        symbol=symbol.upper(),
        timeframe=timeframe,
        candles=len(candles),
        setups=setups,
        triggered=triggered,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        unresolved=unresolved,
        not_triggered=not_triggered,
        target1_hits=target1_hits,
        target2_hits=target2_hits,
        stoploss_hits=stoploss_hits,
        win_rate=win_rate,
        executed_win_rate=executed_win_rate,
        average_r=average_r,
        total_r=total_r,
        profit_factor=profit_factor,
        net_profit_factor=financials["net_profit_factor"],
        initial_capital=round(initial_capital, 2),
        ending_capital=financials["ending_capital"],
        gross_pnl=financials["gross_pnl"],
        total_charges=financials["total_charges"],
        net_pnl=financials["net_pnl"],
        net_return_percent=financials["net_return_percent"],
        expectancy=financials["expectancy"],
        average_winner=financials["average_winner"],
        average_loser=financials["average_loser"],
        max_drawdown=financials["max_drawdown"],
        max_drawdown_percent=financials["max_drawdown_percent"],
        longest_winning_streak=financials["longest_winning_streak"],
        longest_losing_streak=financials["longest_losing_streak"],
        slippage_bps=round(slippage_bps, 2),
        risk_per_trade_percent=round(risk_per_trade_pct, 2),
        max_position_value_percent=round(max_position_value_pct, 2),
        equity_curve=financials["equity_curve"],
        monthly_returns=financials["monthly_returns"],
        trades=tuple(trades),
    )


def backtest_to_dict(result: BacktestResult) -> dict[str, Any]:
    return asdict(result)