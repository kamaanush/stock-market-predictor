"use client";

import { useMemo, type CSSProperties } from "react";
import styles from "./OverviewPanel.module.css";

type LiveStock = {
  symbol: string;
  token?: string;
  ltp: number;
  volume?: number | null;
  exchange_timestamp?: number | string | null;
  received_at?: string;
};

type PortfolioHolding = {
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

type ScannerResult = {
  symbol: string;
  signal: string;
  score: number;
  grade: string;
  trend: string;
  reason: string;
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
  execution: {
    status: string;
    timeframe: string;
    last_price: number;
  };
  ai_analysis?: {
    engine: string;
    market_bias: string;
    trend_analysis: string;
    momentum_analysis: string;
    volume_analysis: string;
    risk_analysis: string;
    recommendation: string;
    overall_summary: string;
  };
};

type OverviewPanelProps = {
  stocks: LiveStock[];
  holdings: PortfolioHolding[];
  scanners: Record<string, ScannerResult>;
  status: string;
  lastMarketUpdate: string | number | null | undefined;
  onOpenScanner: () => void;
  onOpenPortfolio: () => void;
  onSelectSymbol: (sym: string) => void;
};

const money = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "—";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
};

const compactNumber = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "—";

  return new Intl.NumberFormat("en-IN", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
};

const normalizeSymbol = (value: string) =>
  value.toUpperCase().replace(/[\s_\-]/g, "");

const signalTone = (signal?: string) => {
  const value = signal?.toUpperCase();
  if (value === "BUY" || value === "BULLISH") return styles.positive;
  if (value === "SELL" || value === "BEARISH") return styles.negative;
  return styles.neutral;
};

export default function OverviewPanel({
  stocks,
  holdings,
  scanners,
  status,
  lastMarketUpdate,
  onOpenScanner,
  onOpenPortfolio,
  onSelectSymbol,
}: OverviewPanelProps) {
  const portfolio = useMemo(() => {
    const totalValue = holdings.reduce(
      (sum, item) => sum + (item.market_value ?? 0),
      0,
    );
    const totalPnl = holdings.reduce(
      (sum, item) => sum + (item.unrealized_pnl ?? 0),
      0,
    );
    const invested = Math.max(0, totalValue - totalPnl);
    const pnlPercent = invested > 0 ? (totalPnl / invested) * 100 : 0;

    return { totalValue, totalPnl, invested, pnlPercent };
  }, [holdings]);

  const sortedHoldings = useMemo(
    () =>
      [...holdings]
        .sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0))
        .slice(0, 5),
    [holdings],
  );

  const scannerRows = useMemo(
    () =>
      Object.values(scanners)
        .filter(Boolean)
        .sort(
          (a, b) =>
            (b.analysis?.confidence ?? b.score ?? 0) -
            (a.analysis?.confidence ?? a.score ?? 0),
        ),
    [scanners],
  );

  const breadth = useMemo(() => {
    let bullish = 0;
    let bearish = 0;
    let neutral = 0;

    scannerRows.forEach((item) => {
      const signal = item.signal?.toUpperCase();
      const trend = item.trend?.toUpperCase();

      if (signal === "BUY" || trend.includes("BULL")) bullish += 1;
      else if (signal === "SELL" || trend.includes("BEAR")) bearish += 1;
      else neutral += 1;
    });

    const total = bullish + bearish + neutral;
    return {
      bullish,
      bearish,
      neutral,
      total,
      bullishPct: total ? (bullish / total) * 100 : 0,
      bearishPct: total ? (bearish / total) * 100 : 0,
      neutralPct: total ? (neutral / total) * 100 : 0,
    };
  }, [scannerRows]);

  const findIndex = (...aliases: string[]) => {
    const normalizedAliases = aliases.map(normalizeSymbol);
    return stocks.find((stock) =>
      normalizedAliases.includes(normalizeSymbol(stock.symbol)),
    );
  };

  const indices = [
    {
      label: "NIFTY 50",
      stock: findIndex("NIFTY", "NIFTY50", "NIFTY 50", "NIFTY-EQ"),
    },
    {
      label: "SENSEX",
      stock: findIndex("SENSEX", "BSESENSEX"),
    },
    {
      label: "NIFTY BANK",
      stock: findIndex("BANKNIFTY", "NIFTYBANK", "NIFTY BANK"),
    },
    {
      label: "INDIA VIX",
      stock: findIndex("INDIAVIX", "INDIA VIX", "VIX"),
    },
  ];

  const activeSymbols = useMemo(
    () =>
      [...stocks]
        .sort((a, b) => (b.volume ?? 0) - (a.volume ?? 0))
        .slice(0, 5),
    [stocks],
  );

  const live = /LIVE|CONNECTED|OPEN/i.test(status);

  const lastUpdated = useMemo(() => {
    if (!lastMarketUpdate) return "Waiting for feed";
    const date = new Date(lastMarketUpdate);
    if (Number.isNaN(date.getTime())) return lastMarketUpdate;
    return date.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }, [lastMarketUpdate]);

  const topHoldingShare =
    portfolio.totalValue > 0 && sortedHoldings.length > 0
      ? Math.min(
          100,
          ((sortedHoldings[0].market_value ?? 0) / portfolio.totalValue) * 100,
        )
      : 0;

  return (
    <>
ß

      <section className={styles.shell} id="overview-section">
      <div className={styles.portfolioSide}>
        <div className={styles.sideGlow} />

        <div className={styles.sectionHeader}>
          <div>
            <span className={styles.eyebrow}>PORTFOLIO OVERVIEW</span>
            <h2>Your capital at a glance</h2>
          </div>
          <button className={styles.ghostButton} onClick={onOpenPortfolio}>
            OPEN PORTFOLIO ↗
          </button>
        </div>

        <div className={styles.heroMetric}>
          <span>CURRENT VALUE</span>
          <strong>{money(portfolio.totalValue)}</strong>
          <div className={styles.pnlRow}>
            <b
              className={
                portfolio.totalPnl >= 0 ? styles.positive : styles.negative
              }
            >
              {portfolio.totalPnl >= 0 ? "+" : ""}
              {money(portfolio.totalPnl)}
            </b>
            <span>
              {portfolio.totalPnl >= 0 ? "+" : ""}
              {portfolio.pnlPercent.toFixed(2)}%
            </span>
            <small>unrealized P/L</small>
          </div>
        </div>

        <div className={styles.portfolioVisual}>
          <div className={styles.visualHeader}>
            <span>POSITION MAP</span>
            <small>{holdings.length} holdings</small>
          </div>

          <div className={styles.allocationHero}>
            <div
              className={styles.allocationRing}
              style={
                {
                  "--share": `${topHoldingShare * 3.6}deg`,
                } as CSSProperties
              }
            >
              <div>
                <span>TOP</span>
                <strong>{topHoldingShare.toFixed(0)}%</strong>
              </div>
            </div>

            <div className={styles.allocationSummary}>
              <span>INVESTED</span>
              <strong>{money(portfolio.invested)}</strong>
              <p>
                Allocation is calculated from your current holdings. No fake
                historical performance data is shown.
              </p>
            </div>
          </div>

          <div className={styles.holdingBars}>
            {sortedHoldings.length === 0 ? (
              <div className={styles.emptyState}>No portfolio holdings yet.</div>
            ) : (
              sortedHoldings.map((item) => {
                const share = portfolio.totalValue
                  ? ((item.market_value ?? 0) / portfolio.totalValue) * 100
                  : 0;

                return (
                  <button
                    key={item.symbol}
                    className={styles.holdingRow}
                    onClick={() => onSelectSymbol(item.symbol)}
                  >
                    <div className={styles.holdingTopLine}>
                      <strong>{item.symbol}</strong>
                      <span>{money(item.market_value)}</span>
                      <b
                        className={
                          (item.unrealized_pnl ?? 0) >= 0
                            ? styles.positive
                            : styles.negative
                        }
                      >
                        {(item.unrealized_pnl_percent ?? 0) >= 0 ? "+" : ""}
                        {(item.unrealized_pnl_percent ?? 0).toFixed(2)}%
                      </b>
                    </div>
                    <div className={styles.barTrack}>
                      <i style={{ width: `${Math.max(2, share)}%` }} />
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className={styles.quickActions}>
          <button onClick={onOpenScanner} className={styles.primaryButton}>
            <span className={styles.buttonDot} />
            OPEN AI SCANNER
          </button>
          <button onClick={onOpenPortfolio} className={styles.secondaryButton}>
            MANAGE HOLDINGS
          </button>
        </div>
      </div>

      <div className={styles.marketSide}>
        <div className={styles.marketHeader}>
          <div>
            <span className={styles.eyebrowDark}>MARKET OVERVIEW</span>
            <h2>Live intelligence workspace</h2>
          </div>
          <div className={styles.connectionBlock}>
            <span className={live ? styles.liveDot : styles.offlineDot} />
            <div>
              <strong>{status || "UNKNOWN"}</strong>
              <small>Last feed {lastUpdated}</small>
            </div>
          </div>
        </div>

        <div className={styles.indexStrip}>
          {indices.map(({ label, stock }) => (
            <div className={styles.indexCard} key={label}>
              <span>{label}</span>
              <strong>{stock ? money(stock.ltp) : "—"}</strong>
              <small>
                {stock
                  ? `${compactNumber(stock.volume)} volume`
                  : "Feed not in watchlist"}
              </small>
            </div>
          ))}
        </div>

        <div className={styles.marketGrid}>
          <div className={`${styles.panel} ${styles.breadthPanel}`}>
            <div className={styles.panelHeading}>
              <div>
                <span>MARKET BREADTH</span>
                <h3>Scanner consensus</h3>
              </div>
              <strong>{breadth.total}</strong>
            </div>

            <div className={styles.breadthBar}>
              <i
                className={styles.breadthBull}
                style={{ width: `${breadth.bullishPct}%` }}
              />
              <i
                className={styles.breadthNeutral}
                style={{ width: `${breadth.neutralPct}%` }}
              />
              <i
                className={styles.breadthBear}
                style={{ width: `${breadth.bearishPct}%` }}
              />
            </div>

            <div className={styles.breadthStats}>
              <span>
                <i className={styles.bullDot} /> BUY <b>{breadth.bullish}</b>
              </span>
              <span>
                <i className={styles.waitDot} /> WAIT <b>{breadth.neutral}</b>
              </span>
              <span>
                <i className={styles.bearDot} /> SELL <b>{breadth.bearish}</b>
              </span>
            </div>
          </div>

          <div className={`${styles.panel} ${styles.scannerPanel}`}>
            <div className={styles.scanSweep} />
            <div className={styles.panelHeading}>
              <div>
                <span>AI OPPORTUNITIES</span>
                <h3>Highest confidence</h3>
              </div>
              <button onClick={onOpenScanner}>VIEW ALL ↗</button>
            </div>

            <div className={styles.opportunityList}>
              {scannerRows.slice(0, 4).length === 0 ? (
                <div className={styles.emptyStateDark}>
                  AI scanner is waiting for analyzed symbols.
                </div>
              ) : (
                scannerRows.slice(0, 4).map((item, index) => (
                  <button
                    className={styles.opportunityRow}
                    onClick={() => onSelectSymbol(item.symbol)}
                    key={item.symbol}
                  >
                    <span className={styles.rank}>
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className={styles.opportunitySymbol}>
                      <strong>{item.symbol}</strong>
                      <small>{item.execution?.timeframe ?? "—"}</small>
                    </div>
                    <b className={signalTone(item.signal)}>{item.signal}</b>
                    <div className={styles.confidenceCell}>
                      <strong>{item.analysis?.confidence ?? item.score}%</strong>
                      <div className={styles.confidenceTrack}>
                        <i
                          style={{
                            width: `${Math.max(
                              3,
                              item.analysis?.confidence ?? item.score ?? 0,
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                    <span className={styles.grade}>{item.grade}</span>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className={`${styles.panel} ${styles.activePanel}`}>
            <div className={styles.panelHeading}>
              <div>
                <span>ACTIVE SYMBOLS</span>
                <h3>Highest live volume</h3>
              </div>
              <small>{stocks.length} live</small>
            </div>

            <div className={styles.activeList}>
              {activeSymbols.length === 0 ? (
                <div className={styles.emptyStateDark}>Waiting for live market feed.</div>
              ) : (
                activeSymbols.map((stock) => {
                  const scanner = scanners[stock.symbol];
                  return (
                    <button
                      key={stock.symbol}
                      onClick={() => onSelectSymbol(stock.symbol)}
                    >
                      <div>
                        <strong>{stock.symbol}</strong>
                        <small>{compactNumber(stock.volume)} volume</small>
                      </div>
                      <span>{money(stock.ltp)}</span>
                      <b className={signalTone(scanner?.signal)}>
                        {scanner?.signal ?? "LIVE"}
                      </b>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className={`${styles.panel} ${styles.pulsePanel}`}>
            <div className={styles.panelHeading}>
              <div>
                <span>AI MARKET PULSE</span>
                <h3>Current read</h3>
              </div>
            </div>

            <div className={styles.pulseBody}>
              <div className={styles.radar}>
                <span className={styles.radarRing1} />
                <span className={styles.radarRing2} />
                <span className={styles.radarSweep} />
                <strong>
                  {scannerRows[0]?.analysis?.confidence ?? "AI"}
                </strong>
              </div>

              <div className={styles.pulseCopy}>
                <span>LEADING SIGNAL</span>
                <strong
                  className={signalTone(scannerRows[0]?.signal)}
                >
                  {scannerRows[0]?.signal ?? "WAITING"}
                </strong>
                <p>
                  {scannerRows[0]?.analysis?.summary ??
                    "Market pulse will summarize the strongest scanner result once live analysis is available."}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
      </section>
    </>
  );
}