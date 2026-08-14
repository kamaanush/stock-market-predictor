"use client";

import type { FormEvent } from "react";
import styles from "./AlertsPanel.module.css";

type AlertItem = {
  id: number;
  symbol: string;
  name: string;
  condition: "ABOVE" | "BELOW";
  target_price: number;
  delivery: "BROWSER" | "TELEGRAM" | "BOTH";
  active: boolean;
};

type AlertsPanelProps = {
  alerts: AlertItem[];
  busy: boolean;
  message?: string | null;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (alert: AlertItem, active: boolean) => void;
  onDelete: (alert: AlertItem) => void;
  onEnableBrowser?: () => void;
  onRefresh?: () => void;
};

function money(value: number | null | undefined) {
  if (value == null) return "—";
  return `₹${value.toFixed(2)}`;
}

export default function AlertsPanel({
  alerts,
  busy,
  message,
  onSave,
  onToggle,
  onDelete,
  onEnableBrowser,
  onRefresh,
}: AlertsPanelProps) {
  const activeAlerts = alerts.filter((alert) => alert.active);
  const inactiveAlerts = alerts.filter((alert) => !alert.active);
  const browserAlerts = alerts.filter(
    (alert) => alert.delivery === "BROWSER" || alert.delivery === "BOTH"
  );
  const telegramAlerts = alerts.filter(
    (alert) => alert.delivery === "TELEGRAM" || alert.delivery === "BOTH"
  );

  return (
    <section id="alerts-section" className={styles.shell}>
      <header className={styles.hero}>
        <div>
          <span className={styles.kicker}>SMART NOTIFICATIONS</span>
          <h1>Alerts Command Center</h1>
          <p>
            Create price triggers, control delivery channels and manage
            active notifications from one monitoring workspace.
          </p>
        </div>

        <div className={styles.heroActions}>
          {onEnableBrowser && (
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={onEnableBrowser}
            >
              ENABLE BROWSER ALERTS
            </button>
          )}

          {onRefresh && (
            <button
              type="button"
              className={styles.refreshButton}
              onClick={onRefresh}
              disabled={busy}
            >
              {busy ? "REFRESHING…" : "REFRESH"}
            </button>
          )}
        </div>
      </header>

      <div className={styles.metricGrid}>
        <Metric label="TOTAL ALERTS" value={String(alerts.length)} hint="All configured rules" tone="cyan" />
        <Metric label="ACTIVE" value={String(activeAlerts.length)} hint="Currently monitoring" tone="green" />
        <Metric label="PAUSED / TRIGGERED" value={String(inactiveAlerts.length)} hint="Not actively monitoring" tone="amber" />
        <Metric label="DELIVERY CHANNELS" value={`${browserAlerts.length}/${telegramAlerts.length}`} hint="Browser / Telegram" tone="violet" />
      </div>

      {message && <div className={styles.message}>{message}</div>}

      <div className={styles.mainGrid}>
        <section className={styles.alertsCard}>
          <div className={styles.panelHeader}>
            <div>
              <span className={styles.kicker}>ALERT MONITOR</span>
              <h2>Active & triggered rules</h2>
            </div>
            <span className={styles.countBadge}>{alerts.length}</span>
          </div>

          {alerts.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.radar}>
                <span />
                <span />
                <i />
                <strong>ALERT</strong>
              </div>
              <h3>No alerts configured</h3>
              <p>Create a price rule on the right to begin monitoring.</p>
            </div>
          ) : (
            <div className={styles.alertList}>
              {alerts.map((alert) => (
                <article
                  key={alert.id}
                  className={`${styles.alertRow} ${
                    alert.active ? styles.alertActive : styles.alertInactive
                  }`}
                >
                  <div className={styles.alertIdentity}>
                    <div className={styles.symbolIcon}>
                      {alert.condition === "ABOVE" ? "↗" : "↘"}
                    </div>

                    <div>
                      <strong>{alert.symbol}</strong>
                      <small>{alert.name || "NSE instrument"}</small>
                    </div>
                  </div>

                  <div className={styles.conditionBlock}>
                    <span>CONDITION</span>
                    <strong>{alert.condition}</strong>
                  </div>

                  <div className={styles.priceBlock}>
                    <span>TARGET</span>
                    <strong>{money(alert.target_price)}</strong>
                  </div>

                  <div className={styles.deliveryBlock}>
                    <span>DELIVERY</span>
                    <strong>{alert.delivery}</strong>
                  </div>

                  <div className={styles.statusBlock}>
                    <span className={alert.active ? styles.statusLive : styles.statusPaused}>
                      <i />
                      {alert.active ? "MONITORING" : "PAUSED"}
                    </span>
                  </div>

                  <div className={styles.actions}>
                    <button
                      type="button"
                      className={styles.actionButton}
                      onClick={() => onToggle(alert, !alert.active)}
                    >
                      {alert.active ? "PAUSE" : "REACTIVATE"}
                    </button>

                    <button
                      type="button"
                      className={styles.deleteButton}
                      onClick={() => onDelete(alert)}
                      title={`Delete ${alert.symbol} alert`}
                    >
                      ×
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <aside className={styles.sideColumn}>
          <form onSubmit={onSave} className={styles.createCard}>
            <div className={styles.formHeading}>
              <span className={styles.kicker}>CREATE ALERT</span>
              <h2>New price trigger</h2>
            </div>

            <div className={styles.formGrid}>
              <label>
                <span>NSE SYMBOL</span>
                <input name="symbol" required placeholder="e.g. RELIANCE" />
              </label>

              <label>
                <span>COMPANY NAME</span>
                <input name="name" placeholder="Optional" />
              </label>

              <label>
                <span>TRIGGER CONDITION</span>
                <select name="condition" defaultValue="ABOVE">
                  <option value="ABOVE">Price rises above</option>
                  <option value="BELOW">Price falls below</option>
                </select>
              </label>

              <label>
                <span>TARGET PRICE</span>
                <input
                  name="target_price"
                  type="number"
                  min="0.01"
                  step="any"
                  required
                  placeholder="0.00"
                />
              </label>

              <label>
                <span>DELIVERY</span>
                <select name="delivery" defaultValue="BROWSER">
                  <option value="BROWSER">Browser</option>
                  <option value="TELEGRAM">Telegram</option>
                  <option value="BOTH">Browser + Telegram</option>
                </select>
              </label>
            </div>

            <button type="submit" className={styles.primaryButton}>
              SAVE ALERT <span>↗</span>
            </button>
          </form>

          <section className={styles.deliveryCard}>
            <div className={styles.formHeading}>
              <span className={styles.kicker}>DELIVERY STATUS</span>
              <h2>Notification channels</h2>
            </div>

            <div className={styles.channelList}>
              <Channel title="Browser" count={browserAlerts.length} active={browserAlerts.length > 0} />
              <Channel title="Telegram" count={telegramAlerts.length} active={telegramAlerts.length > 0} />
            </div>
          </section>
        </aside>
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
  tone: "cyan" | "green" | "amber" | "violet";
}) {
  return (
    <div className={`${styles.metric} ${styles[`metric_${tone}`]}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

function Channel({
  title,
  count,
  active,
}: {
  title: string;
  count: number;
  active: boolean;
}) {
  return (
    <div className={styles.channel}>
      <div>
        <strong>{title}</strong>
        <small>{count} configured</small>
      </div>
      <span className={active ? styles.channelOn : styles.channelOff}>
        <i />
        {active ? "READY" : "IDLE"}
      </span>
    </div>
  );
}