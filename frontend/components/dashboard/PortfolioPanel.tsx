import type { FormEvent } from "react";
import Metric from "./Metric";
import { money, number } from "./format";
import type { Holding } from "./types";

export default function PortfolioPanel({
  holdings,
  totalPnl,
  totalValue,
  onSave,
  onImport,
  busy,
}: {
  holdings: Holding[];
  totalPnl: number;
  totalValue: number;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onImport: (
    event: FormEvent<HTMLFormElement>,
  ) => void;
  busy: boolean;
}) {
  return (
    <>
      <p className="text-xs tracking-[.18em] text-accent">
        HOLDINGS
      </p>

      <h1 className="mt-1 text-3xl font-semibold">
        Portfolio
      </h1>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Metric
          label="Current value"
          value={money(totalValue)}
        />

        <Metric
          label="Unrealized P/L"
          value={money(totalPnl)}
          positive={totalPnl >= 0}
        />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.7fr_.8fr]">
        <div className="border border-line bg-panel">
          <div className="grid grid-cols-5 border-b border-line px-4 py-3 text-xs text-muted">
            <span>SYMBOL</span>
            <span>QTY</span>
            <span>AVG</span>
            <span>CURRENT</span>
            <span>P/L</span>
          </div>

          {holdings.length === 0 ? (
            <p className="p-6 text-sm text-muted">
              Add a holding below, or import a CSV with
              symbol, name, quantity, average_price, and
              optional token.
            </p>
          ) : (
            holdings.map((item) => (
              <div
                className="grid grid-cols-5 px-4 py-4"
                key={item.symbol}
              >
                <b>{item.symbol}</b>
                <span>{number(item.quantity)}</span>
                <span>{money(item.average_price)}</span>
                <span>{money(item.current_price)}</span>
                <span
                  className={
                    (item.unrealized_pnl || 0) >= 0
                      ? "text-accent"
                      : "text-red-400"
                  }
                >
                  {money(item.unrealized_pnl)}
                </span>
              </div>
            ))
          )}
        </div>

        <div className="space-y-6">
          <form
            onSubmit={onSave}
            className="border border-line bg-panel p-5"
          >
            <h2 className="mb-4 font-semibold">
              Add or update holding
            </h2>

            <div className="space-y-3">
              {[
                ["symbol", "NSE symbol e.g. RELIANCE"],
                ["name", "Company name"],
                ["token", "Angel token (optional in demo)"],
                ["quantity", "Quantity"],
                ["averagePrice", "Average buy price"],
              ].map(([name, placeholder]) => (
                <input
                  key={name}
                  name={name}
                  required={name !== "token"}
                  type={
                    name === "quantity" ||
                    name === "averagePrice"
                      ? "number"
                      : "text"
                  }
                  min={
                    name === "quantity" ||
                    name === "averagePrice"
                      ? "0.01"
                      : undefined
                  }
                  step="any"
                  placeholder={placeholder}
                  className="w-full border border-line bg-ink px-3 py-2.5 outline-none focus:border-accent"
                />
              ))}

              <button className="w-full bg-accent px-4 py-2.5 font-bold text-black">
                Save holding
              </button>
            </div>
          </form>

          <form
            onSubmit={onImport}
            className="border border-line bg-panel p-5"
          >
            <h2 className="mb-2 font-semibold">
              Import CSV
            </h2>

            <p className="mb-4 text-xs leading-5 text-muted">
              Headers: symbol, name, quantity,
              average_price. Token is optional.
            </p>

            <input
              name="file"
              type="file"
              accept=".csv,text/csv"
              className="mb-3 block w-full text-sm text-muted file:mr-3 file:border-0 file:bg-[#173b21] file:px-3 file:py-2 file:text-[#bdeecb]"
            />

            <button
              disabled={busy}
              className="w-full border border-accent px-4 py-2.5 font-semibold text-accent disabled:opacity-60"
            >
              {busy ? "Importing…" : "Import CSV"}
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
