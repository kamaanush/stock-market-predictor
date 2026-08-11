import type { FormEvent } from "react";
import { money } from "./format";
import type { Alert } from "./types";

export default function AlertsPanel({
  alerts,
  onSave,
  onToggle,
  onDelete,
}: {
  alerts: Alert[];
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (alert: Alert, active: boolean) => void;
  onDelete: (alert: Alert) => void;
}) {
  return (
    <>
      <p className="text-xs tracking-[.18em] text-accent">
        NOTIFICATIONS
      </p>

      <h1 className="mt-1 text-3xl font-semibold">
        Alerts
      </h1>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_.8fr]">
        <div className="border border-line bg-panel">
          {alerts.length === 0 ? (
            <p className="p-6 text-sm text-muted">
              No alerts yet. Configure a target price to
              receive browser sound or Telegram
              notifications.
            </p>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between gap-4 border-b border-line px-5 py-4"
              >
                <span>
                  <b>{alert.symbol}</b>
                  <span className="ml-3 text-muted">
                    {alert.condition}{" "}
                    {money(alert.target_price)}
                  </span>
                </span>

                <span className="flex items-center gap-3">
                  <span
                    className={
                      alert.active
                        ? "text-xs text-accent"
                        : "text-xs text-muted"
                    }
                  >
                    {alert.active
                      ? alert.delivery
                      : "TRIGGERED"}
                  </span>

                  <button
                    onClick={() =>
                      onToggle(alert, !alert.active)
                    }
                    className="text-xs text-muted hover:text-accent"
                  >
                    {alert.active
                      ? "Pause"
                      : "Reactivate"}
                  </button>

                  <button
                    onClick={() => onDelete(alert)}
                    className="text-lg text-muted hover:text-red-400"
                    title="Delete alert"
                  >
                    ×
                  </button>
                </span>
              </div>
            ))
          )}
        </div>

        <form
          onSubmit={onSave}
          className="border border-line bg-panel p-5"
        >
          <h2 className="mb-4 font-semibold">
            Create alert
          </h2>

          <div className="space-y-3">
            <input
              name="symbol"
              required
              placeholder="NSE symbol"
              className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
            />

            <input
              name="name"
              placeholder="Company name (optional)"
              className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
            />

            <select
              name="condition"
              className="w-full border border-line bg-ink px-3 py-2.5"
            >
              <option value="ABOVE">
                Price rises above
              </option>
              <option value="BELOW">
                Price falls below
              </option>
            </select>

            <input
              name="targetPrice"
              required
              min="0.01"
              step="any"
              type="number"
              placeholder="Target price"
              className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
            />

            <select
              name="delivery"
              className="w-full border border-line bg-ink px-3 py-2.5"
            >
              <option value="BROWSER">
                Browser sound
              </option>
              <option value="TELEGRAM">
                Telegram
              </option>
              <option value="BOTH">
                Browser + Telegram
              </option>
            </select>

            <button className="w-full bg-accent px-4 py-2.5 font-bold text-black">
              Save alert
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
