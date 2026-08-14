"use client";

import StockChart, { Candle } from "../StockChart";
import styles from "./WatchlistPanel.module.css";

type Timeframe = "15s" | "1m" | "5m" | "15m";

type LiveStock = {
  symbol: string;
  token?: string;
  ltp: number;
  volume?: number | null;
  exchange_timestamp?: number | string | null;
  received_at?: string;
};

type ScannerResult = {
  symbol: string;
  signal: string;
  score: number;
  grade: string;
  trend: string;
  reason: string;

  technical_analysis: {
    ema: string;
    ema_fast: number;
    ema_slow: number;
    supertrend: string;
    supertrend_value: number;
    adx: number;
    plus_di: number;
    minus_di: number;
    trend_strength: string;
    rsi: number;
    macd: string;
    macd_value: number;
    macd_signal: number;
    vwap: string;
    vwap_value: number;
    volume: string;
    volume_value: number;
    average_volume: number;
    atr: number;
    pattern: string | null;
    pattern_direction: string | null;
    pattern_confidence: number | null;
  };

  cpr?: {
    pivot: number;
    top_central: number;
    bottom_central: number;
    width: number;
    width_percent: number;
    classification: string;
    position: string;
  };

  trade_plan: {
    entry: number | null;
    stoploss: number | null;
    target1: number | null;
    target2: number | null;
    risk_reward: string;
  };

  analysis: {
    engine: string;
    confidence: number;
    probability_label: string;
    risk_label: string;
    summary: string;
  };

  ai_analysis: {
    engine: string;
    market_bias: string;
    trend_analysis: string;
    momentum_analysis: string;
    volume_analysis: string;
    risk_analysis: string;
    recommendation: string;
    overall_summary: string;
  };

  execution: {
    status: string;
    timeframe: string;
    last_price: number;
  };
};

type WatchlistPanelProps = {
  stocks: LiveStock[];
  sortedStocks: LiveStock[];
  selected: string;
  selectedStock: LiveStock | undefined;
  scanners: Record<string, ScannerResult>;
  selectedScanner: ScannerResult | undefined;
  timeframe: Timeframe;
  chartData: Candle[];
  chartLoading: boolean;
  lastMarketUpdate: string;
  onSelectSymbol: (symbol: string) => void;
  onTimeframeChange: (value: Timeframe) => void;
};

function money(value: number | null | undefined) {
  if (value == null) return "—";
  return `₹${value.toFixed(2)}`;
}

function signalClass(signal?: string) {
  const value = (signal || "").toUpperCase();
  if (value === "BUY") return styles.buy;
  if (value === "SELL") return styles.sell;
  return styles.wait;
}

function trendClass(trend?: string) {
  const value = (trend || "").toUpperCase();
  if (value === "BULLISH") return styles.bullish;
  if (value === "BEARISH") return styles.bearish;
  return styles.neutral;
}

export default function WatchlistPanel({
  stocks,
  sortedStocks,
  selected,
  selectedStock,
  scanners,
  selectedScanner,
  timeframe,
  chartData,
  chartLoading,
  lastMarketUpdate,
  onSelectSymbol,
  onTimeframeChange,
}: WatchlistPanelProps) {
  return (
    <section id="watchlist-section" className={styles.shell}>
      <header className={styles.topHeader}>
        <div>
          <span className={styles.kicker}>LIVE TRADING WORKSPACE</span>
          <h1>Watchlist & Chart</h1>
          <p>
            Select a symbol, inspect live candles and review the latest AI scanner
            context in one trading workspace.
          </p>
        </div>

        <div className={styles.feedStatus}>
          <span className={styles.liveDot} />
          <div>
            <strong>LIVE FEED</strong>
            <small>
              {lastMarketUpdate
                ? new Date(lastMarketUpdate).toLocaleTimeString("en-IN")
                : "Waiting for feed"}
            </small>
          </div>
        </div>
      </header>

      <div className={styles.mainGrid}>
        {/* LEFT WATCHLIST RAIL */}
        <aside className={styles.watchRail}>
          <div className={styles.railHeader}>
            <span>WATCHLIST</span>
            <b>{stocks.length}</b>
          </div>

          <div className={styles.watchList}>
            {sortedStocks.length === 0 ? (
              <div className={styles.emptyRail}>
                Waiting for Angel One live market data...
              </div>
            ) : (
              sortedStocks.map((stock) => {
                const scanner = scanners[stock.symbol];
                const active = selected === stock.symbol;

                return (
                  <button
                    key={stock.symbol}
                    type="button"
                    onClick={() => onSelectSymbol(stock.symbol)}
                    className={`${styles.watchItem} ${
                      active ? styles.watchItemActive : ""
                    }`}
                  >
                    <div className={styles.symbolBlock}>
                      <strong>{stock.symbol}</strong>
                      <small>{stock.volume ?? "—"} VOL</small>
                    </div>

                    <div className={styles.priceBlock}>
                      <strong>{money(stock.ltp)}</strong>

                      {scanner ? (
                        <span
                          className={`${styles.signalMini} ${signalClass(
                            scanner.signal
                          )}`}
                        >
                          {scanner.signal}
                        </span>
                      ) : (
                        <span className={styles.liveMini}>LIVE</span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        {/* CENTER CHART */}
        <main className={styles.chartPanel}>
          <div className={styles.chartHeader}>
            <div>
              <span className={styles.kicker}>SELECTED SYMBOL</span>

              <div className={styles.titleRow}>
                <h2>{selected || "SELECT STOCK"}</h2>

                {selectedScanner && (
                  <span
                    className={`${styles.signalPill} ${signalClass(
                      selectedScanner.signal
                    )}`}
                  >
                    {selectedScanner.signal}
                  </span>
                )}
              </div>

              {selectedScanner && (
                <div className={styles.scannerStrip}>
                  <span className={trendClass(selectedScanner.trend)}>
                    {selectedScanner.trend}
                  </span>
                  <span>
                    CONFIDENCE {selectedScanner.analysis.confidence}%
                  </span>
                  <span>{selectedScanner.analysis.probability_label}</span>
                  <span>GRADE {selectedScanner.grade}</span>
                </div>
              )}
            </div>

            <div className={styles.priceHero}>
              <small>LIVE PRICE</small>
              <strong>
                {selectedStock ? money(selectedStock.ltp) : "—"}
              </strong>
              <span>{selectedScanner?.execution.status || "WAITING"}</span>
            </div>
          </div>

          <div className={styles.toolbar}>
            <div className={styles.timeframes}>
              {(["15s", "1m", "5m", "15m"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => onTimeframeChange(value)}
                  className={timeframe === value ? styles.timeframeActive : ""}
                >
                  {value}
                </button>
              ))}
            </div>

            <div className={styles.chartMetaTop}>
              <span>{chartData.length} CANDLES</span>
              <span>EMA 20</span>
              <span>VOLUME</span>
            </div>
          </div>

          <div className={styles.chartCanvas}>
            {chartLoading && chartData.length === 0 ? (
              <div className={styles.chartEmpty}>
                <div className={styles.loadingLine} />
                <strong>LOADING MARKET DATA</strong>
                <span>
                  Loading {timeframe} candles for {selected || "selected stock"}
                </span>
              </div>
            ) : chartData.length > 0 ? (
              <StockChart data={chartData} interval={timeframe} />
            ) : (
              <div className={styles.chartEmpty}>
                <div className={styles.radarEmpty}>
                  <span />
                  <span />
                  <i />
                  <strong>LIVE</strong>
                </div>

                <strong>WAITING FOR CANDLES</strong>
                <span>No {timeframe} candles available.</span>
              </div>
            )}
          </div>

          <div className={styles.bottomStats}>
            <div>
              <span>TIMEFRAME</span>
              <strong>{timeframe}</strong>
            </div>
            <div>
              <span>CANDLES</span>
              <strong>{chartData.length}</strong>
            </div>
            <div>
              <span>AI SIGNAL</span>
              <strong>{selectedScanner?.signal || "—"}</strong>
            </div>
            <div>
              <span>CONFIDENCE</span>
              <strong>
                {selectedScanner
                  ? `${selectedScanner.analysis.confidence}%`
                  : "—"}
              </strong>
            </div>
          </div>
        </main>

        {/* RIGHT AI LENS */}
        <aside className={styles.aiLens}>
          <div className={styles.lensHeader}>
            <div>
              <span className={styles.kicker}>AI TRADE LENS</span>
              <h2>{selectedScanner?.symbol || "NO SETUP"}</h2>
            </div>

            {selectedScanner && (
              <span
                className={`${styles.signalLarge} ${signalClass(
                  selectedScanner.signal
                )}`}
              >
                {selectedScanner.signal}
              </span>
            )}
          </div>

          {selectedScanner ? (
            <>
              <div className={styles.confidenceCard}>
                <div className={styles.confidenceRing}>
                  <span className={styles.ringOuter} />
                  <span className={styles.ringInner} />
                  <i
                    style={{
                      transform: `rotate(${
                        -135 + selectedScanner.analysis.confidence * 2.7
                      }deg)`,
                    }}
                  />
                  <strong>{selectedScanner.analysis.confidence}%</strong>
                  <small>CONFIDENCE</small>
                </div>

                <div className={styles.confidenceDetails}>
                  <span>
                    TREND
                    <strong className={trendClass(selectedScanner.trend)}>
                      {selectedScanner.trend}
                    </strong>
                  </span>

                  <span>
                    GRADE
                    <strong>{selectedScanner.grade}</strong>
                  </span>

                  <span>
                    RISK
                    <strong>{selectedScanner.analysis.risk_label}</strong>
                  </span>
                </div>
              </div>

              <div className={styles.techGrid}>
                <Metric
                  label="RSI"
                  value={selectedScanner.technical_analysis.rsi.toFixed(1)}
                />
                <Metric
                  label="ADX"
                  value={selectedScanner.technical_analysis.adx.toFixed(1)}
                />
                <Metric
                  label="EMA"
                  value={selectedScanner.technical_analysis.ema}
                />
                <Metric
                  label="VWAP"
                  value={selectedScanner.technical_analysis.vwap}
                />
                <Metric
                  label="MACD"
                  value={selectedScanner.technical_analysis.macd}
                />
                <Metric
                  label="VOLUME"
                  value={selectedScanner.technical_analysis.volume}
                />
              </div>

              <div className={styles.tradePlan}>
                <div className={styles.tradePlanTitle}>
                  <span>EXECUTION PLAN</span>
                  <small>{selectedScanner.execution.timeframe}</small>
                </div>

                <div className={styles.planGrid}>
                  <Plan label="ENTRY" value={money(selectedScanner.trade_plan.entry)} />
                  <Plan
                    label="STOP"
                    value={money(selectedScanner.trade_plan.stoploss)}
                    danger
                  />
                  <Plan
                    label="TARGET 1"
                    value={money(selectedScanner.trade_plan.target1)}
                  />
                  <Plan
                    label="TARGET 2"
                    value={money(selectedScanner.trade_plan.target2)}
                  />
                </div>

                <div className={styles.rrRow}>
                  <span>RISK / REWARD</span>
                  <strong>{selectedScanner.trade_plan.risk_reward || "—"}</strong>
                </div>
              </div>

              <div className={styles.summary}>
                <span>AI SUMMARY</span>
                <p>{selectedScanner.ai_analysis.overall_summary}</p>
              </div>
            </>
          ) : (
            <div className={styles.noLens}>
              <div className={styles.radarLarge}>
                <span />
                <span />
                <i />
                <strong>AI</strong>
              </div>

              <h3>No scanner result selected</h3>
              <p>
                Select a watched symbol with scanner data to open its AI trade
                lens.
              </p>
            </div>
          )}
        </aside>
      </div>

      {selectedScanner && (
        <div className={styles.insightRail}>
          <Insight title="TREND" text={selectedScanner.ai_analysis.trend_analysis} />
          <Insight
            title="MOMENTUM"
            text={selectedScanner.ai_analysis.momentum_analysis}
          />
          <Insight title="VOLUME" text={selectedScanner.ai_analysis.volume_analysis} />
          <Insight title="RISK" text={selectedScanner.ai_analysis.risk_analysis} />
        </div>
      )}
    </section>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className={styles.metric}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Plan({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div className={danger ? styles.planDanger : styles.plan}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Insight({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <div className={styles.insight}>
      <span>{title}</span>
      <p>{text}</p>
    </div>
  );
}