import type { Candle } from "../StockChart";

export type View = "watchlist" | "portfolio" | "alerts";

export type Instrument = {
  symbol: string;
  name: string;
  token: string;
  kind: string;
};

export type WatchItem = Instrument & {
  last_price: number | null;
  change_percent: number | null;
};

export type Holding = {
  symbol: string;
  name: string;
  token: string;
  quantity: number;
  average_price: number;
  current_price: number | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_percent: number | null;
};

export type Alert = {
  id: number;
  symbol: string;
  name: string;
  condition: "ABOVE" | "BELOW";
  target_price: number;
  delivery: "BROWSER" | "TELEGRAM" | "BOTH";
  active: boolean;
};

export type AlertEvent = {
  id: number;
  alert_id: number;
  symbol: string;
  message: string;
  delivery: "BROWSER" | "TELEGRAM" | "BOTH";
  created_at: string;
};

export type TimeframeRisk = {
  level: string;
  risk_score: number;
  reward_risk_ratio: number | null;
  stop_distance_percent: number | null;
  target_distance_percent: number | null;
  warnings: string[];
  positives: string[];
  summary: string;
};

export type TimeframeDecision = {
  signal: string;
  confidence: number;
  grade: string;
  action: string;
  summary: string;
};

export type TimeframeConfidence = {
  signal: string;
  confidence: number;
  grade: string;
  probability: string;
  positive_score: number;
  penalty_score: number;
  summary: string;
};

export type TimeframeAnalysis = {
  decision: TimeframeDecision;
  market_structure: Record<string, unknown>;
  trend_strength: Record<string, unknown>;
  momentum: Record<string, unknown>;
  participation: Record<string, unknown>;
  buyer_seller_pressure: Record<string, unknown>;
  candle_flow: Record<string, unknown>;
  location: Record<string, unknown>;
  risk: TimeframeRisk;
  breakout_readiness: Record<string, unknown>;
  confidence: TimeframeConfidence;
};

export type MarketOpportunity = {
  symbol: string;
  name: string | null;
  signal: "BUY" | "SELL" | "WAIT";
  confidence: number;
  grade: string;
  action: string;
  alignment: string;
  strongest_timeframe: string;
  timeframes: Record<string, TimeframeAnalysis>;
};

export type MarketScanResponse = {
  scanned: number;
  successful: number;
  failed: number;
  opportunities: MarketOpportunity[];
  failures: {
    symbol: string;
    error: string;
  }[];
};

export type { Candle };
