"use client";

import type { FormEvent } from "react";
import styles from "./PortfolioPanel.module.css";

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

type PortfolioPanelProps = {
  holdings: PortfolioHolding[];
  totalPnl: number;
  totalValue: number;
  busy: boolean;
  message?: string;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onImport: (event: FormEvent<HTMLFormElement>) => void;
  onRefresh?: () => void;
};

function money(value: number | null | undefined) {
  if (value == null) return "—";
  return `₹${value.toFixed(2)}`;
}

function percent(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export default function PortfolioPanel({
  holdings,
  totalPnl,
  totalValue,
  busy,
  message,
  onSave,
  onImport,
  onRefresh,
}: PortfolioPanelProps) {
  const totalCost = holdings.reduce(
    (sum, item) => sum + item.average_price * item.quantity,
    0
  );

  const totalPnlPercent =
    totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

  const sortedByValue = [...holdings].sort(
    (a, b) => (b.market_value || 0) - (a.market_value || 0)
  );

  const biggestHolding = sortedByValue[0];

  const bestPerformer = [...holdings].sort(
    (a, b) =>
      (b.unrealized_pnl_percent || 0) -
      (a.unrealized_pnl_percent || 0)
  )[0];

  const worstPerformer = [...holdings].sort(
    (a, b) =>
      (a.unrealized_pnl_percent || 0) -
      (b.unrealized_pnl_percent || 0)
  )[0];

  return (
    <section id="portfolio-section" className={styles.shell}>
      <header className={styles.hero}>
        <div>
          <span className={styles.kicker}>PORTFOLIO INTELLIGENCE</span>
          <h1>Your capital, positions & exposure</h1>
          <p>
            Monitor live holdings, unrealized P/L and concentration while
            keeping add/update and CSV import tools in the same workspace.
          </p>
        </div>

        <div className={styles.heroActions}>
          {onRefresh && (
            <button
              type="button"
              className={styles.refreshButton}
              onClick={onRefresh}
              disabled={busy}
            >
              {busy ? "REFRESHING…" : "REFRESH PORTFOLIO"}
            </button>
          )}
        </div>
      </header>

      <div className={styles.metricGrid}>
        <Metric
          label="CURRENT VALUE"
          value={money(totalValue)}
          hint={`${holdings.length} holding${holdings.length === 1 ? "" : "s"}`}
          tone="cyan"
        />

        <Metric
          label="UNREALIZED P/L"
          value={money(totalPnl)}
          hint={percent(totalPnlPercent)}
          tone={totalPnl >= 0 ? "green" : "red"}
        />

        <Metric
          label="INVESTED COST"
          value={money(totalCost)}
          hint="Average cost × quantity"
          tone="violet"
        />

        <Metric
          label="TOP EXPOSURE"
          value={biggestHolding?.symbol || "—"}
          hint={
            biggestHolding && totalValue > 0
              ? `${(
                  ((biggestHolding.market_value || 0) / totalValue) *
                  100
                ).toFixed(1)}% of portfolio`
              : "No exposure yet"
          }
          tone="amber"
        />
      </div>

      {message && <div className={styles.message}>{message}</div>}

      <div className={styles.mainGrid}>
        <section className={styles.allocationCard}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>ALLOCATION</span>
              <h2>Position map</h2>
            </div>
            <span className={styles.countBadge}>{holdings.length}</span>
          </div>

          {holdings.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyOrb}>
                <span />
                <span />
                <strong>₹</strong>
              </div>
              <h3>No holdings yet</h3>
              <p>Add a position or import a CSV to build your portfolio map.</p>
            </div>
          ) : (
            <div className={styles.allocationBody}>
              <div className={styles.donut}>
                <div className={styles.donutInner}>
                  <span>PORTFOLIO</span>
                  <strong>{holdings.length}</strong>
                  <small>POSITIONS</small>
                </div>
              </div>

              <div className={styles.allocationList}>
                {sortedByValue.slice(0, 6).map((item) => {
                  const weight =
                    totalValue > 0
                      ? ((item.market_value || 0) / totalValue) * 100
                      : 0;

                  return (
                    <div key={item.symbol} className={styles.allocationRow}>
                      <div>
                        <strong>{item.symbol}</strong>
                        <small>{item.name}</small>
                      </div>

                      <div className={styles.weightBlock}>
                        <span>{weight.toFixed(1)}%</span>
                        <i>
                          <b style={{ width: `${Math.max(2, weight)}%` }} />
                        </i>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <section className={styles.performanceCard}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>PERFORMANCE</span>
              <h2>P/L intelligence</h2>
            </div>
          </div>

          <div className={styles.performanceHero}>
            <div>
              <span>NET UNREALIZED</span>
              <strong
                className={
                  totalPnl >= 0 ? styles.positiveText : styles.negativeText
                }
              >
                {money(totalPnl)}
              </strong>
              <small>{percent(totalPnlPercent)} vs invested cost</small>
            </div>

            <div className={styles.performancePulse}>
              <span />
              <span />
              <i />
              <strong>{totalPnl >= 0 ? "UP" : "DOWN"}</strong>
            </div>
          </div>

          <div className={styles.performanceSplit}>
            <div>
              <span>BEST PERFORMER</span>
              <strong>{bestPerformer?.symbol || "—"}</strong>
              <small
                className={
                  (bestPerformer?.unrealized_pnl_percent || 0) >= 0
                    ? styles.positiveText
                    : styles.negativeText
                }
              >
                {percent(bestPerformer?.unrealized_pnl_percent)}
              </small>
            </div>

            <div>
              <span>WEAKEST PERFORMER</span>
              <strong>{worstPerformer?.symbol || "—"}</strong>
              <small
                className={
                  (worstPerformer?.unrealized_pnl_percent || 0) >= 0
                    ? styles.positiveText
                    : styles.negativeText
                }
              >
                {percent(worstPerformer?.unrealized_pnl_percent)}
              </small>
            </div>
          </div>

          <div className={styles.exposureBars}>
            {sortedByValue.slice(0, 5).map((item) => {
              const pnl = item.unrealized_pnl_percent || 0;
              const width = Math.min(100, Math.max(3, Math.abs(pnl) * 8));

              return (
                <div key={item.symbol} className={styles.exposureRow}>
                  <span>{item.symbol}</span>
                  <i>
                    <b
                      className={pnl >= 0 ? styles.barPositive : styles.barNegative}
                      style={{ width: `${width}%` }}
                    />
                  </i>
                  <strong
                    className={pnl >= 0 ? styles.positiveText : styles.negativeText}
                  >
                    {percent(pnl)}
                  </strong>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      <section className={styles.holdingsCard}>
        <div className={styles.panelHeader}>
          <div>
            <span className={styles.kicker}>LIVE HOLDINGS</span>
            <h2>Position breakdown</h2>
          </div>
          <span className={styles.tableMeta}>
            {holdings.length} STOCK{holdings.length === 1 ? "" : "S"}
          </span>
        </div>

        <div className={styles.tableWrap}>
          <div className={styles.tableHead}>
            <span>SYMBOL</span>
            <span>QTY</span>
            <span>AVG</span>
            <span>CURRENT</span>
            <span>VALUE</span>
            <span>P/L</span>
            <span>RETURN</span>
          </div>

          {holdings.length === 0 ? (
            <div className={styles.emptyTable}>No holdings loaded yet.</div>
          ) : (
            holdings.map((item) => {
              const positive = (item.unrealized_pnl || 0) >= 0;

              return (
                <div className={styles.tableRow} key={item.symbol}>
                  <span className={styles.symbolCell}>
                    <strong>{item.symbol}</strong>
                    <small>{item.name}</small>
                  </span>
                  <span>{item.quantity}</span>
                  <span>{money(item.average_price)}</span>
                  <span>{money(item.current_price)}</span>
                  <span>{money(item.market_value)}</span>
                  <span className={positive ? styles.positiveText : styles.negativeText}>
                    {money(item.unrealized_pnl)}
                  </span>
                  <span className={positive ? styles.returnPositive : styles.returnNegative}>
                    {percent(item.unrealized_pnl_percent)}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </section>

      <div className={styles.toolsGrid}>
        <form onSubmit={onSave} className={styles.formCard}>
          <div className={styles.formHeading}>
            <span className={styles.kicker}>POSITION MANAGER</span>
            <h2>Add or update holding</h2>
          </div>

          <div className={styles.formGrid}>
            <Field name="symbol" placeholder="NSE symbol e.g. RELIANCE" />
            <Field name="name" placeholder="Company name" />
            <Field name="token" placeholder="Angel token (optional)" required={false} />
            <Field name="quantity" placeholder="Quantity" type="number" />
            <Field name="average_price" placeholder="Average buy price" type="number" />
          </div>

          <button className={styles.primaryButton} type="submit">
            SAVE HOLDING <span>↗</span>
          </button>
        </form>

        <form onSubmit={onImport} className={styles.importCard}>
          <div className={styles.formHeading}>
            <span className={styles.kicker}>BULK IMPORT</span>
            <h2>Import portfolio CSV</h2>
          </div>

          <p>
            Supported headers: symbol, name, quantity, average_price.
            Token is optional.
          </p>

          <label className={styles.fileBox}>
            <span>CSV FILE</span>
            <input name="file" type="file" accept=".csv,text/csv" />
          </label>

          <button
            className={styles.secondaryButton}
            type="submit"
            disabled={busy}
          >
            {busy ? "IMPORTING…" : "IMPORT CSV"}
          </button>
        </form>
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

function Field({
  name,
  placeholder,
  type = "text",
  required = true,
}: {
  name: string;
  placeholder: string;
  type?: "text" | "number";
  required?: boolean;
}) {
  return (
    <input
      name={name}
      required={required}
      type={type}
      min={type === "number" ? "0.01" : undefined}
      step={type === "number" ? "any" : undefined}
      placeholder={placeholder}
      className={styles.input}
    />
  );
}