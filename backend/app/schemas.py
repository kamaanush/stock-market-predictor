from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


class InstrumentOut(ORMModel):
    symbol: str
    name: str
    token: str
    kind: str


class WatchlistCreate(InstrumentOut):
    pass


class WatchlistOut(InstrumentOut):
    last_price: Optional[float] = None
    change_percent: Optional[float] = None


class QuoteOut(BaseModel):
    symbol: str
    last_price: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None
    change_percent: Optional[float] = None
    updated_at: datetime


class HoldingInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    token: str = ""
    quantity: float = Field(gt=0)
    average_price: float = Field(gt=0)


class HoldingOut(HoldingInput):
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percent: Optional[float] = None


class AlertInput(BaseModel):
    symbol: str
    name: str = ""
    condition: str = Field(pattern="^(ABOVE|BELOW)$")
    target_price: float = Field(gt=0)
    delivery: str = Field(default="BROWSER", pattern="^(BROWSER|TELEGRAM|BOTH)$")
    note: str = ""


class AlertOut(AlertInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    active: bool
    last_triggered_at: Optional[datetime] = None


class AlertEventOut(ORMModel):
    id: int
    alert_id: int
    symbol: str
    message: str
    delivery: str
    created_at: datetime


class CandleOut(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0


class ScannerResultOut(BaseModel):
    symbol: str
    signal: str
    score: int
    grade: str
    trend: str
    reason: str
    entry_price: Optional[float] = None
    stoploss: Optional[float] = None
    target1: Optional[float] = None
    target2: Optional[float] = None
    action_status: str
    pattern: Optional[str] = None
    pattern_direction: Optional[str] = None
    pattern_confidence: Optional[int] = None

class TechnicalAnalysisOut(BaseModel):
    ema: str
    ema_fast: float
    ema_slow: float

    supertrend: str
    supertrend_value: float

    adx: float
    plus_di: float
    minus_di: float
    trend_strength: str

    rsi: float
    macd: str
    macd_value: float
    macd_signal: float

    vwap: str
    vwap_value: float

    volume: str
    volume_value: float
    average_volume: float

    atr: float

    pattern: Optional[str] = None
    pattern_direction: Optional[str] = None
    pattern_confidence: Optional[int] = None


class TradePlanOut(BaseModel):
    entry: Optional[float] = None
    stoploss: Optional[float] = None
    target1: Optional[float] = None
    target2: Optional[float] = None
    risk_reward: Optional[str] = None


class AnalysisOut(BaseModel):
    engine: str
    confidence: int
    probability_label: str
    risk_label: str
    summary: str


class ExecutionOut(BaseModel):
    status: str
    timeframe: str
    last_price: float

class AIAnalysisOut(BaseModel):
    engine: str
    market_bias: str
    trend_analysis: str
    momentum_analysis: str
    volume_analysis: str
    risk_analysis: str
    recommendation: str
    overall_summary: str

class CPRAnalysisOut(BaseModel):
    pivot: float
    top_central: float
    bottom_central: float
    width: float
    width_percent: float
    classification: str
    position: str

class ScannerV2Out(BaseModel):
    symbol: str
    signal: str
    score: int
    grade: str
    trend: str
    reason: str

    technical_analysis: TechnicalAnalysisOut
    cpr: CPRAnalysisOut
    trade_plan: TradePlanOut
    analysis: AnalysisOut
    ai_analysis: AIAnalysisOut
    execution: ExecutionOut