"use client";

import styles from "./AnalyticsPanel.module.css";

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

type AnalyticsPanelProps = {
  stocks: LiveStock[];
  scanners: Record<string, ScannerResult>;
  lastMarketUpdate: string;
  onSelectSymbol?: (symbol: string) => void;
};

function money(value: number | null | undefined) {
  if (value == null) return "—";
  return `₹${value.toFixed(2)}`;
}

function signalClass(signal: string) {
  const value = signal.toUpperCase();
  if (value === "BUY") return styles.buy;
  if (value === "SELL") return styles.sell;
  return styles.wait;
}

export default function AnalyticsPanel({
  stocks,
  scanners,
  lastMarketUpdate,
  onSelectSymbol,
}: AnalyticsPanelProps) {
  const scannerList = Object.values(scanners);

  const buyCount = scannerList.filter(
    (item) => item.signal.toUpperCase() === "BUY"
  ).length;

  const sellCount = scannerList.filter(
    (item) => item.signal.toUpperCase() === "SELL"
  ).length;

  const waitCount = Math.max(0, scannerList.length - buyCount - sellCount);

  const bullishCount = scannerList.filter(
    (item) => item.trend.toUpperCase() === "BULLISH"
  ).length;

  const bearishCount = scannerList.filter(
    (item) => item.trend.toUpperCase() === "BEARISH"
  ).length;

  const averageConfidence =
    scannerList.length > 0
      ? scannerList.reduce(
          (sum, item) => sum + item.analysis.confidence,
          0
        ) / scannerList.length
      : 0;

  const averageRsi =
    scannerList.length > 0
      ? scannerList.reduce(
          (sum, item) => sum + item.technical_analysis.rsi,
          0
        ) / scannerList.length
      : 0;

  const averageAdx =
    scannerList.length > 0
      ? scannerList.reduce(
          (sum, item) => sum + item.technical_analysis.adx,
          0
        ) / scannerList.length
      : 0;

  const topOpportunities = [...scannerList]
    .sort((a, b) => b.analysis.confidence - a.analysis.confidence)
    .slice(0, 5);

  const volumeLeaders = [...stocks]
    .sort((a, b) => (b.volume || 0) - (a.volume || 0))
    .slice(0, 5);

  const marketBias =
    bullishCount > bearishCount
      ? "BULLISH"
      : bearishCount > bullishCount
        ? "BEARISH"
        : "BALANCED";

  const coverage =
    stocks.length > 0 ? (scannerList.length / stocks.length) * 100 : 0;

  return (
    <section id="analytics-section" className={styles.shell}>
      <header className={styles.hero}>
        <div>
          <span className={styles.kicker}>MARKET INTELLIGENCE</span>
          <h1>Analytics Control Room</h1>
          <p>
            Live breadth, scanner confidence, momentum and liquidity
            intelligence from your current market feed.
          </p>
        </div>

        <div className={styles.marketState}>
          <span className={styles.liveDot} />
          <div>
            <strong>{marketBias} BIAS</strong>
            <small>
              {lastMarketUpdate
                ? new Date(lastMarketUpdate).toLocaleTimeString("en-IN")
                : "Waiting for feed"}
            </small>
          </div>
        </div>
      </header>

      <div className={styles.metricGrid}>
        <Metric
          label="ANALYZED"
          value={`${scannerList.length}/${stocks.length}`}
          hint={`${coverage.toFixed(1)}% coverage`}
          tone="cyan"
        />
        <Metric
          label="AVG CONFIDENCE"
          value={`${averageConfidence.toFixed(1)}%`}
          hint="Scanner-wide average"
          tone="violet"
        />
        <Metric
          label="MARKET BREADTH"
          value={marketBias}
          hint={`${bullishCount} bull / ${bearishCount} bear`}
          tone={marketBias === "BULLISH" ? "green" : marketBias === "BEARISH" ? "red" : "amber"}
        />
        <Metric
          label="AVG ADX"
          value={averageAdx.toFixed(1)}
          hint={`RSI ${averageRsi.toFixed(1)}`}
          tone="amber"
        />
      </div>

      <div className={styles.mainGrid}>
        <section className={styles.card}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>SIGNAL DISTRIBUTION</span>
              <h2>Scanner pressure</h2>
            </div>
          </div>

          <div className={styles.signalGrid}>
            <Signal label="BUY" value={buyCount} className={styles.positiveText} />
            <Signal label="SELL" value={sellCount} className={styles.negativeText} />
            <Signal label="WAIT" value={waitCount} className={styles.warningText} />
          </div>

          <div className={styles.breadthBars}>
            <Breadth label="BULLISH" value={bullishCount} total={scannerList.length} kind="positive" />
            <Breadth label="BEARISH" value={bearishCount} total={scannerList.length} kind="negative" />
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>MARKET PULSE</span>
              <h2>Scanner health</h2>
            </div>
          </div>

          <div className={styles.pulseGrid}>
            <Stat label="AVG RSI" value={averageRsi.toFixed(1)} />
            <Stat label="AVG ADX" value={averageAdx.toFixed(1)} />
            <Stat label="TOP CONF" value={topOpportunities[0] ? `${topOpportunities[0].analysis.confidence}%` : "—"} />
            <Stat label="TOP GRADE" value={topOpportunities[0]?.grade || "—"} />
          </div>

          <div className={styles.summaryBox}>
            <span>AI MARKET SUMMARY</span>
            <p>
              {topOpportunities[0]
                ? topOpportunities[0].ai_analysis.overall_summary
                : "Scanner intelligence will appear after symbols are analyzed."}
            </p>
          </div>
        </section>
      </div>

      <div className={styles.secondaryGrid}>
        <section className={styles.card}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>OPPORTUNITY RANKING</span>
              <h2>Highest-confidence setups</h2>
            </div>
          </div>

          <div className={styles.list}>
            {topOpportunities.length === 0 ? (
              <div className={styles.empty}>No scanner results yet.</div>
            ) : (
              topOpportunities.map((item, index) => (
                <button
                  key={item.symbol}
                  type="button"
                  className={styles.opportunityRow}
                  onClick={() => onSelectSymbol?.(item.symbol)}
                >
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <strong>{item.symbol}</strong>
                  <span className={`${styles.signalPill} ${signalClass(item.signal)}`}>
                    {item.signal}
                  </span>
                  <span>{item.analysis.confidence}%</span>
                  <span>{item.trend}</span>
                  <span>{item.grade}</span>
                </button>
              ))
            )}
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>LIQUIDITY</span>
              <h2>Volume leaders</h2>
            </div>
          </div>

          <div className={styles.list}>
            {volumeLeaders.map((stock, index) => (
              <div className={styles.volumeRow} key={stock.symbol}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{stock.symbol}</strong>
                  <small>{money(stock.ltp)}</small>
                </div>
                <span>{stock.volume ?? "—"}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  tone: "cyan" | "green" | "red" | "violet" | "amber";
}) {
  return (
    <div className={`${styles.metric} ${styles[`metric_${tone}`]}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

function Signal({
  label,
  value,
  className,
}: {
  label: string;
  value: number;
  className: string;
}) {
  return (
    <div className={styles.signalCard}>
      <span>{label}</span>
      <strong className={className}>{value}</strong>
    </div>
  );
}

function Breadth({
  label,
  value,
  total,
  kind,
}: {
  label: string;
  value: number;
  total: number;
  kind: "positive" | "negative";
}) {
  const width = total > 0 ? (value / total) * 100 : 0;

  return (
    <div className={styles.breadthRow}>
      <span>{label}</span>
      <i>
        <b
          className={kind === "positive" ? styles.barPositive : styles.barNegative}
          style={{ width: `${Math.max(2, width)}%` }}
        />
      </i>
      <strong>{width.toFixed(1)}%</strong>
    </div>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className={styles.stat}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}