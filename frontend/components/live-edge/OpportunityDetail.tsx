"use client";

type OpportunityData = {
  symbol: string;
  ltp: number;
  opportunity_score: number;
  opportunity_state: string;

  rvol?: number;
  rvol_source?: string;

  movement_reasons?: string[];
  movement_components?: Record<string, unknown>;

  relative_strength?: {
    rs_1m_percent?: number;
    rs_3m_percent?: number;
    rs_5m_percent?: number;
    strength?: number;
    persistence?: string;
    direction?: string;
  };

  change_1m_percent?: number;
  change_5m_percent?: number;

  fast_score?: number;

  compression_state?: string;
  compression_score?: number;

  liquidity_sweep?: string;
  liquidity_sweep_quality?: number;

  context_setup?: string;
  context_direction?: string;
  context_quality?: number;
};

function n(
  value: unknown,
  digits = 2,
) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed.toFixed(digits)
    : "—";
}

function pct(
  value: unknown,
) {
  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    return "—";
  }

  return `${parsed >= 0 ? "+" : ""}${parsed.toFixed(3)}%`;
}

function Metric({
  title,
  value,
  note,
}: {
  title: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
      <div className="text-xs uppercase text-slate-500">
        {title}
      </div>

      <div className="mt-2 text-lg font-bold text-white">
        {value}
      </div>

      {note && (
        <div className="mt-1 text-xs text-slate-500">
          {note}
        </div>
      )}
    </div>
  );
}

export default function OpportunityDetail({
  item,
  onClose,
}: {
  item: OpportunityData;
  onClose: () => void;
}) {
  const rs = item.relative_strength || {};

  const reasons =
    item.movement_reasons || [];

  const components =
    Object.entries(
      item.movement_components || {},
    );

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <aside
        className="h-full w-full max-w-2xl overflow-y-auto border-l border-slate-800 bg-slate-950 p-6"
        onClick={(event) =>
          event.stopPropagation()
        }
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
              Opportunity Intelligence
            </div>

            <h2 className="mt-2 text-3xl font-bold">
              {item.symbol}
            </h2>

            <div className="mt-1 text-slate-400">
              ₹{n(item.ltp)}
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm"
          >
            Close
          </button>
        </div>

        <div className="mt-6 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-400">
                Movement Opportunity
              </div>

              <div className="mt-1 text-xl font-semibold">
                {item.opportunity_state}
              </div>
            </div>

            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-5 py-3 text-3xl font-bold text-red-300">
              {n(
                item.opportunity_score,
                1,
              )}
            </div>
          </div>

          <div className="mt-3 text-xs text-slate-500">
            Movement-ranking score, not BUY/SELL probability.
          </div>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <Metric
            title="Time RVOL"
            value={`${n(item.rvol)}x`}
            note={
              item.rvol_source ||
              "Unknown source"
            }
          />

          <Metric
            title="Fast Score"
            value={n(
              item.fast_score,
              1,
            )}
          />

          <Metric
            title="1 Minute"
            value={pct(
              item.change_1m_percent,
            )}
          />

          <Metric
            title="5 Minute"
            value={pct(
              item.change_5m_percent,
            )}
          />
        </div>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h3 className="text-lg font-semibold">
            Relative Strength vs NIFTY
          </h3>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric
              title="1m RS"
              value={pct(
                rs.rs_1m_percent,
              )}
            />

            <Metric
              title="3m RS"
              value={pct(
                rs.rs_3m_percent,
              )}
            />

            <Metric
              title="5m RS"
              value={pct(
                rs.rs_5m_percent,
              )}
            />

            <Metric
              title="Strength"
              value={n(
                rs.strength,
                3,
              )}
            />
          </div>

          <div className="mt-4 text-xs text-slate-400">
            Direction:{" "}
            {rs.direction || "UNKNOWN"}
            {" · "}
            Persistence:{" "}
            {rs.persistence || "UNKNOWN"}
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h3 className="text-lg font-semibold">
            Setup Context
          </h3>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Metric
              title="Compression"
              value={
                item.compression_state ||
                "NONE"
              }
              note={`Score ${n(
                item.compression_score,
                1,
              )}`}
            />

            <Metric
              title="Liquidity Sweep"
              value={
                item.liquidity_sweep ||
                "NONE"
              }
              note={`Quality ${n(
                item.liquidity_sweep_quality,
              )}`}
            />

            <Metric
              title="Context"
              value={
                item.context_setup ||
                "NO_CONFLUENCE"
              }
            />

            <Metric
              title="Context Direction"
              value={
                item.context_direction ||
                "NONE"
              }
              note={`Quality ${n(
                item.context_quality,
              )}`}
            />
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h3 className="text-lg font-semibold">
            Why Watch?
          </h3>

          <div className="mt-4 space-y-2">
            {reasons.length === 0 && (
              <div className="text-sm text-slate-500">
                No detailed reasons available.
              </div>
            )}

            {reasons.map(
              (reason, index) => (
                <div
                  key={`${reason}-${index}`}
                  className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300"
                >
                  <span className="mr-2 text-cyan-400">
                    •
                  </span>

                  {reason}
                </div>
              ),
            )}
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <h3 className="text-lg font-semibold">
            Score Components
          </h3>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {components.length === 0 && (
              <div className="text-sm text-slate-500">
                Component telemetry unavailable.
              </div>
            )}

            {components.map(
              ([key, value]) => (
                <div
                  key={key}
                  className="rounded-xl border border-slate-800 bg-slate-950 p-3"
                >
                  <div className="text-xs text-slate-500">
                    {key
                      .replaceAll(
                        "_",
                        " ",
                      )
                      .toUpperCase()}
                  </div>

                  <div className="mt-1 font-semibold">
                    {typeof value ===
                    "number"
                      ? n(value)
                      : String(value)}
                  </div>
                </div>
              ),
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}
