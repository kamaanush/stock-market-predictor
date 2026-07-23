from datetime import datetime

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
    last_price: float | None = None
    change_percent: float | None = None


class QuoteOut(BaseModel):
    symbol: str
    last_price: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    change_percent: float | None = None
    updated_at: datetime


class HoldingInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    token: str = ""
    quantity: float = Field(gt=0)
    average_price: float = Field(gt=0)


class HoldingOut(HoldingInput):
    current_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_percent: float | None = None


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
    last_triggered_at: datetime | None = None


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
