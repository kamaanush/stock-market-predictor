import type { MarketOpportunity } from "./types";

export default function MultiTimeframeDetail({
  opportunity,
}: {
  opportunity: MarketOpportunity;
}) {
  const orderedTimeframes = ["1m", "5m", "15m"].filter(
    (timeframe) => opportunity.timeframes[timeframe],
  );

  return (
    <div className="mb-6 border border-line bg-panel">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line p-4">
        <div>
          <p className="text-xs tracking-[.18em] text-accent">
            MULTI-TIMEFRAME INTELLIGENCE
          </p>

          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold">
              {opportunity.symbol}
            </h2>

            <span
              className={
                opportunity.signal === "BUY"
                  ? "font-bold text-accent"
                  : opportunity.signal === "SELL"
                    ? "font-bold text-red-400"
                    : "font-bold text-yellow-300"
              }
            >
              {opportunity.signal}
            </span>

            <span className="text-sm text-muted">
              {opportunity.confidence}% confidence
            </span>

            <span className="text-sm text-muted">
              Grade {opportunity.grade}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 text-right text-xs">
          <div>
            <p className="text-muted">ACTION</p>
            <p
              className={
                opportunity.action === "ACTIVE"
                  ? "mt-1 font-semibold text-accent"
                  : "mt-1 font-semibold text-yellow-300"
              }
            >
              {opportunity.action}
            </p>
          </div>

          <div>
            <p className="text-muted">ALIGNMENT</p>
            <p className="mt-1 font-semibold">
              {opportunity.alignment}
            </p>
          </div>

          <div>
            <p className="text-muted">BEST TF</p>
            <p className="mt-1 font-semibold text-accent">
              {opportunity.strongest_timeframe}
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1180px] text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs text-muted">
              <th className="p-3">TIMEFRAME</th>
              <th className="p-3">SIGNAL</th>
              <th className="p-3">CONFIDENCE</th>
              <th className="p-3">ACTION</th>
              <th className="p-3">RISK</th>
              <th className="p-3">TREND</th>
              <th className="p-3">MOMENTUM</th>
              <th className="p-3">PRESSURE</th>
              <th className="p-3">CANDLE FLOW</th>
              <th className="p-3">BREAKOUT</th>
            </tr>
          </thead>

          <tbody>
            {orderedTimeframes.map((timeframe) => {
              const item = opportunity.timeframes[timeframe];

              const trendStrength =
                item.trend_strength as {
                  classification?: string;
                  direction?: string;
                  adx?: number;
                };

              const momentum =
                item.momentum as {
                  classification?: string;
                  direction?: string;
                  rsi?: number;
                };

              const pressure =
                item.buyer_seller_pressure as {
                  pressure?: string;
                  dominance?: string;
                  buyers_score?: number;
                  sellers_score?: number;
                };

              const candleFlow =
                item.candle_flow as {
                  direction?: string;
                  strength?: string;
                  score?: number;
                };

              const breakout =
                item.breakout_readiness as {
                  status?: string;
                  readiness_score?: number;
                };

              return (
                <tr
                  key={timeframe}
                  className={
                    timeframe === opportunity.strongest_timeframe
                      ? "border-b border-line/60 bg-[#102016]"
                      : "border-b border-line/60"
                  }
                >
                  <td className="p-3">
                    <span className="font-bold text-accent">
                      {timeframe}
                    </span>
                    {timeframe === opportunity.strongest_timeframe && (
                      <span className="ml-2 text-[10px] text-yellow-300">
                        BEST
                      </span>
                    )}
                  </td>

                  <td className="p-3">
                    <span
                      className={
                        item.decision.signal === "BUY"
                          ? "font-bold text-accent"
                          : item.decision.signal === "SELL"
                            ? "font-bold text-red-400"
                            : "font-bold text-yellow-300"
                      }
                    >
                      {item.decision.signal}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{item.confidence.confidence}%</b>
                    <span className="ml-2 text-xs text-muted">
                      {item.confidence.probability}
                    </span>
                  </td>

                  <td className="p-3">
                    {item.decision.action}
                  </td>

                  <td
                    className={
                      item.risk.level === "VERY HIGH" ||
                      item.risk.level === "HIGH"
                        ? "p-3 text-red-400"
                        : item.risk.level === "MEDIUM"
                          ? "p-3 text-yellow-300"
                          : "p-3 text-accent"
                    }
                  >
                    {item.risk.level}
                  </td>

                  <td className="p-3">
                    <b>{trendStrength.direction || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      {trendStrength.classification || "—"} · ADX{" "}
                      {trendStrength.adx ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{momentum.direction || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      {momentum.classification || "—"} · RSI{" "}
                      {momentum.rsi ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{pressure.pressure || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      B {pressure.buyers_score ?? "—"} / S{" "}
                      {pressure.sellers_score ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{candleFlow.direction || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      {candleFlow.strength || "—"} · Score{" "}
                      {candleFlow.score ?? "—"}
                    </span>
                  </td>

                  <td className="p-3">
                    <b>{breakout.status || "—"}</b>
                    <span className="mt-1 block text-xs text-muted">
                      Readiness {breakout.readiness_score ?? "—"}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 border-t border-line p-4 lg:grid-cols-3">
        {orderedTimeframes.map((timeframe) => {
          const item = opportunity.timeframes[timeframe];

          return (
            <div
              key={`${timeframe}-summary`}
              className="border border-line bg-ink/60 p-4"
            >
              <div className="mb-2 flex items-center justify-between">
                <b className="text-accent">
                  {timeframe.toUpperCase()} SUMMARY
                </b>

                <span className="text-xs text-muted">
                  Risk {item.risk.risk_score}/100
                </span>
              </div>

              <p className="text-xs leading-5 text-muted">
                {item.decision.summary}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
