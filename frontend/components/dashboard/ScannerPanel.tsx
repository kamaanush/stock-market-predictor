"use client";

import { useMemo } from "react";
import styles from "./ScannerPanel.module.css";

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

type ScannerPanelProps = {
  stocks: LiveStock[];
  scanners: Record<string, ScannerResult>;
  selected: string;
  scannerLoading: boolean;
  status: string;
  lastMarketUpdate: string;
  onSelectSymbol: (symbol: string) => void;
  onOpenChart: (symbol: string) => void;
};

const money = (value: number | null | undefined) =>
  value == null ? "—" : `₹${value.toFixed(2)}`;

const signalClass = (signal: string) => {
  const value = signal.toUpperCase();
  if (value === "BUY") return styles.buy;
  if (value === "SELL") return styles.sell;
  return styles.wait;
};

export default function ScannerPanel({
  stocks,
  scanners,
  selected,
  scannerLoading,
  status,
  lastMarketUpdate,
  onSelectSymbol,
  onOpenChart,
}: ScannerPanelProps) {
  const ranked = useMemo(() => {
    return Object.values(scanners)
      .sort((a, b) => b.analysis.confidence - a.analysis.confidence)
      .slice(0, 8);
  }, [scanners]);

  const selectedScanner =
    scanners[selected] ?? ranked[0] ?? undefined;

  const buyCount = ranked.filter(
    (item) => item.signal.toUpperCase() === "BUY"
  ).length;
  const sellCount = ranked.filter(
    (item) => item.signal.toUpperCase() === "SELL"
  ).length;
  const waitCount = Math.max(0, ranked.length - buyCount - sellCount);

  const strongest = ranked[0];
  const avgConfidence =
    ranked.length > 0
      ? Math.round(
          ranked.reduce(
            (sum, item) => sum + item.analysis.confidence,
            0
          ) / ranked.length
        )
      : 0;

  const selectedLive = selectedScanner
    ? stocks.find((stock) => stock.symbol === selectedScanner.symbol)
    : undefined;

  return (
    <section id="scanner-section" className={styles.scannerShell}>
      <div className={styles.scanGlow} />
      <div className={styles.scanLine} />

      <header className={styles.hero}>
        <div>
          <div className={styles.kicker}>AI SCANNER / LIVE NSE</div>
          <h1>Opportunity Intelligence</h1>
          <p>
            Scanner signals are ranked by confidence, trend quality and
            executable trade structure.
          </p>
        </div>

        <div className={styles.heroStatus}>
          <div className={styles.liveBadge}>
            <span className={scannerLoading ? styles.pulseDot : styles.dot} />
            {scannerLoading ? "SCANNING" : status === "LIVE" ? "LIVE SCAN" : status}
          </div>
          <small>
            {lastMarketUpdate
              ? `Updated ${new Date(lastMarketUpdate).toLocaleTimeString("en-IN")}`
              : "Waiting for market feed"}
          </small>
        </div>
      </header>

      <div className={styles.statsRow}>
        <Metric label="Analyzed" value={String(ranked.length)} accent="cyan" />
        <Metric label="Buy setups" value={String(buyCount)} accent="green" />
        <Metric label="Sell setups" value={String(sellCount)} accent="red" />
        <Metric label="Avg confidence" value={`${avgConfidence}%`} accent="violet" />
        <Metric
          label="Leader"
          value={strongest?.symbol ?? "WAITING"}
          accent="amber"
        />
      </div>

      <div className={styles.mainGrid}>
        <div className={styles.opportunityBoard}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.panelKicker}>RANKED OPPORTUNITIES</span>
              <h2>Highest-conviction setups</h2>
            </div>
            <div className={styles.signalLegend}>
              <span><i className={styles.legendBuy} /> BUY {buyCount}</span>
              <span><i className={styles.legendWait} /> WAIT {waitCount}</span>
              <span><i className={styles.legendSell} /> SELL {sellCount}</span>
            </div>
          </div>

          <div className={styles.tableHead}>
            <span>#</span>
            <span>SYMBOL</span>
            <span>SIGNAL</span>
            <span>CONF</span>
            <span>TREND</span>
            <span>ENTRY</span>
            <span>R:R</span>
          </div>

          <div className={styles.rows}>
            {ranked.length === 0 ? (
              <div className={styles.emptyState}>
                <div className={styles.scannerOrb}>
                  <div />
                  <div />
                  <strong>AI</strong>
                </div>
                <h3>Waiting for analyzed symbols</h3>
                <p>
                  Once the backend scanner returns results, ranked opportunities
                  will appear here automatically.
                </p>
              </div>
            ) : (
              ranked.map((item, index) => {
                const active = item.symbol === selectedScanner?.symbol;
                const live = stocks.find((s) => s.symbol === item.symbol);

                return (
                  <button
                    key={item.symbol}
                    className={`${styles.opportunityRow} ${
                      active ? styles.activeRow : ""
                    }`}
                    onClick={() => onSelectSymbol(item.symbol)}
                    style={{ animationDelay: `${index * 55}ms` }}
                  >
                    <span className={styles.rank}>{String(index + 1).padStart(2, "0")}</span>

                    <span className={styles.symbolCell}>
                      <strong>{item.symbol}</strong>
                      <small>
                        {live ? money(live.ltp) : money(item.execution.last_price)}
                      </small>
                    </span>

                    <span className={`${styles.signal} ${signalClass(item.signal)}`}>
                      {item.signal}
                    </span>

                    <span className={styles.confidenceCell}>
                      <strong>{item.analysis.confidence}%</strong>
                      <i>
                        <b style={{ width: `${Math.max(3, item.analysis.confidence)}%` }} />
                      </i>
                    </span>

                    <span className={styles.trend}>{item.trend}</span>
                    <span className={styles.numeric}>{money(item.trade_plan.entry)}</span>
                    <span className={styles.numeric}>{item.trade_plan.risk_reward || "—"}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <aside className={styles.aiLens}>
          <div className={styles.lensHeader}>
            <div>
              <span className={styles.panelKicker}>AI TRADE LENS</span>
              <h2>{selectedScanner?.symbol ?? "NO SYMBOL"}</h2>
            </div>

            {selectedScanner && (
              <span className={`${styles.signalLarge} ${signalClass(selectedScanner.signal)}`}>
                {selectedScanner.signal}
              </span>
            )}
          </div>

          {selectedScanner ? (
            <>
              <div className={styles.priceStrip}>
                <div>
                  <span>LIVE PRICE</span>
                  <strong>
                    {money(selectedLive?.ltp ?? selectedScanner.execution.last_price)}
                  </strong>
                </div>
                <div>
                  <span>CONFIDENCE</span>
                  <strong>{selectedScanner.analysis.confidence}%</strong>
                </div>
                <div>
                  <span>GRADE</span>
                  <strong>{selectedScanner.grade}</strong>
                </div>
              </div>

              <div className={styles.radarStage}>
                <div className={styles.radarCircle}>
                  <span className={styles.ringA} />
                  <span className={styles.ringB} />
                  <span className={styles.ringC} />
                  <span className={styles.radarSweep} />
                  <strong>{selectedScanner.analysis.confidence}</strong>
                  <small>AI SCORE</small>
                </div>

                <div className={styles.radarCopy}>
                  <span>MARKET BIAS</span>
                  <strong>{selectedScanner.ai_analysis.market_bias}</strong>
                  <p>{selectedScanner.ai_analysis.overall_summary}</p>
                </div>
              </div>

              <div className={styles.technicalGrid}>
                <Technical
                  label="RSI"
                  value={selectedScanner.technical_analysis.rsi.toFixed(1)}
                />
                <Technical
                  label="ADX"
                  value={selectedScanner.technical_analysis.adx.toFixed(1)}
                />
                <Technical
                  label="EMA"
                  value={selectedScanner.technical_analysis.ema}
                />
                <Technical
                  label="VWAP"
                  value={selectedScanner.technical_analysis.vwap}
                />
                <Technical
                  label="MACD"
                  value={selectedScanner.technical_analysis.macd}
                />
                <Technical
                  label="VOLUME"
                  value={selectedScanner.technical_analysis.volume}
                />
              </div>

              <div className={styles.tradePlan}>
                <div className={styles.tradePlanTitle}>
                  <span>EXECUTION PLAN</span>
                  <small>{selectedScanner.execution.timeframe}</small>
                </div>
                <div className={styles.tradePlanGrid}>
                  <PlanItem label="ENTRY" value={money(selectedScanner.trade_plan.entry)} />
                  <PlanItem label="STOP" value={money(selectedScanner.trade_plan.stoploss)} danger />
                  <PlanItem label="TARGET 1" value={money(selectedScanner.trade_plan.target1)} />
                  <PlanItem label="TARGET 2" value={money(selectedScanner.trade_plan.target2)} />
                </div>
              </div>

              <button
                className={styles.openChartButton}
                onClick={() => onOpenChart(selectedScanner.symbol)}
              >
                OPEN {selectedScanner.symbol} LIVE CHART
                <span>↗</span>
              </button>
            </>
          ) : (
            <div className={styles.lensEmpty}>
              Select an analyzed symbol to open the AI trade lens.
            </div>
          )}
        </aside>
      </div>

      {selectedScanner && (
        <div className={styles.insightRail}>
          <Insight
            title="TREND"
            text={selectedScanner.ai_analysis.trend_analysis}
          />
          <Insight
            title="MOMENTUM"
            text={selectedScanner.ai_analysis.momentum_analysis}
          />
          <Insight
            title="VOLUME"
            text={selectedScanner.ai_analysis.volume_analysis}
          />
          <Insight
            title="RISK"
            text={selectedScanner.ai_analysis.risk_analysis}
          />
        </div>
      )}
    </section>
  );
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "cyan" | "green" | "red" | "violet" | "amber";
}) {
  return (
    <div className={`${styles.metric} ${styles[`metric_${accent}`]}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Technical({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.technicalItem}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PlanItem({
  label,
  value,
  danger = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div className={danger ? styles.planDanger : styles.planItem}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Insight({ title, text }: { title: string; text: string }) {
  return (
    <div className={styles.insight}>
      <span>{title}</span>
      <p>{text}</p>
    </div>
  );
}
