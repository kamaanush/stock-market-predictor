import StockChart from "../StockChart";
import MultiTimeframeDetail from "./MultiTimeframeDetail";
import { money } from "./format";
import type {
  Candle,
  Instrument,
  MarketOpportunity,
  MarketScanResponse,
  WatchItem,
} from "./types";

export default function WatchlistPanel({
  watchlist,
  selected,
  query,
  matches,
  interval,
  candles,
  marketScan,
  selectedOpportunity,
  scannerBusy,
  autoScannerEnabled,
  lastScannerRun,
  onSearch,
  onAdd,
  onRemove,
  onSelect,
  onInterval,
  onRunScanner,
  onSelectOpportunity,
  onToggleAutoScanner,
}: {
  watchlist: WatchItem[];
  selected: WatchItem | null;
  query: string;
  matches: Instrument[];
  interval: string;
  candles: Candle[];
  marketScan: MarketScanResponse | null;
  selectedOpportunity: MarketOpportunity | null;
  scannerBusy: boolean;
  autoScannerEnabled: boolean;
  lastScannerRun: string | null;
  onSearch: (value: string) => void;
  onAdd: (item: Instrument) => void;
  onRemove: (symbol: string) => void;
  onSelect: (item: WatchItem) => void;
  onInterval: (value: string) => void;
  onRunScanner: () => void;
  onSelectOpportunity: (item: MarketOpportunity) => void;
  onToggleAutoScanner: () => void;
}) {
  return (
    <>
      <div className="mb-6 flex items-end justify-between gap-5">
        <div>
          <p className="text-xs tracking-[.18em] text-accent">
            MARKET OVERVIEW
          </p>
          <h1 className="mt-1 text-3xl font-semibold">
            Watchlist
          </h1>
        </div>

        <div className="relative w-80">
          <input
            value={query}
            onChange={(event) =>
              onSearch(event.target.value)
            }
            placeholder="Search NSE symbol or company"
            className="w-full border border-line bg-panel px-3 py-2.5 outline-none focus:border-accent"
          />

          {matches.length > 0 && (
            <div className="absolute z-10 mt-1 w-full border border-line bg-[#0b120d] shadow-xl">
              {matches.map((item) => (
                <button
                  key={`${item.symbol}-${item.token}`}
                  onClick={() => onAdd(item)}
                  className="flex w-full items-center justify-between px-3 py-3 text-left hover:bg-[#13321c]"
                >
                  <span>
                    <b>{item.symbol}</b>
                    <span className="ml-2 text-xs text-muted">
                      {item.name}
                    </span>
                  </span>

                  <span className="text-xs text-accent">
                    ADD
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mb-6 border border-line bg-panel">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line p-4">
          <div>
            <p className="text-xs tracking-[.18em] text-accent">
              AI SCANNER
            </p>

            <h2 className="mt-1 text-xl font-semibold">
              V2 Multi-Timeframe Opportunities
            </h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="text-right text-xs text-muted">
              <p>
                Auto scan:{" "}
                <span
                  className={
                    autoScannerEnabled
                      ? "text-accent"
                      : "text-yellow-300"
                  }
                >
                  {autoScannerEnabled ? "ON" : "OFF"}
                </span>
              </p>

              <p>
                Last scan:{" "}
                {lastScannerRun || "Not run yet"}
              </p>
            </div>

            <button
              onClick={onToggleAutoScanner}
              disabled={watchlist.length === 0}
              className="border border-line px-4 py-2 font-semibold text-muted hover:border-accent hover:text-accent disabled:opacity-50"
            >
              {autoScannerEnabled
                ? "Stop Auto Scan"
                : "Start Auto Scan"}
            </button>

            <button
              onClick={onRunScanner}
              disabled={
                scannerBusy || watchlist.length === 0
              }
              className="bg-accent px-4 py-2 font-bold text-black disabled:opacity-50"
            >
              {scannerBusy ? "Scanning…" : "Run V2 Scan"}
            </button>
          </div>
        </div>

        {!marketScan || marketScan.opportunities.length === 0 ? (
          <div className="p-5 text-sm text-muted">
            <p>
              Run the V2 market scanner to analyze and rank your watchlist
              across 1m, 5m, and 15m.
            </p>

            {marketScan && marketScan.failures.length > 0 && (
              <div className="mt-3 space-y-1 text-xs text-red-300">
                {marketScan.failures.map((failure) => (
                  <p key={failure.symbol}>
                    {failure.symbol}: {failure.error}
                  </p>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-muted">
                  <th className="p-3">Rank</th>
                  <th className="p-3">Symbol</th>
                  <th className="p-3">Signal</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Grade</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">Alignment</th>
                  <th className="p-3">Best TF</th>
                  <th className="p-3">Risk</th>
                </tr>
              </thead>

              <tbody>
                {marketScan.opportunities.map((result, index) => {
                  const strongest =
                    result.timeframes[result.strongest_timeframe];
                  const risk = strongest?.risk?.level || "—";

                  return (
                    <tr
                      key={result.symbol}
                      onClick={() => onSelectOpportunity(result)}
                      className={`cursor-pointer border-b border-line/60 hover:bg-[#102016] ${
                        selectedOpportunity?.symbol === result.symbol
                          ? "bg-[#12301b]"
                          : ""
                      }`}
                    >
                      <td className="p-3 text-muted">
                        {String(index + 1).padStart(2, "0")}
                      </td>

                      <td className="p-3">
                        <b>{result.symbol}</b>
                        {result.name && (
                          <span className="ml-2 text-xs text-muted">
                            {result.name}
                          </span>
                        )}
                      </td>

                      <td className="p-3">
                        <span
                          className={
                            result.signal === "BUY"
                              ? "font-bold text-accent"
                              : result.signal === "SELL"
                                ? "font-bold text-red-400"
                                : "font-bold text-yellow-300"
                          }
                        >
                          {result.signal}
                        </span>
                      </td>

                      <td className="p-3 font-semibold">
                        {result.confidence}%
                      </td>

                      <td className="p-3">
                        {result.grade}
                      </td>

                      <td className="p-3">
                        <span
                          className={
                            result.action === "ACTIVE"
                              ? "font-semibold text-accent"
                              : "text-yellow-300"
                          }
                        >
                          {result.action}
                        </span>
                      </td>

                      <td className="p-3">
                        {result.alignment}
                      </td>

                      <td className="p-3 font-semibold text-accent">
                        {result.strongest_timeframe}
                      </td>

                      <td
                        className={`p-3 ${
                          risk === "VERY HIGH" || risk === "HIGH"
                            ? "text-red-400"
                            : risk === "MEDIUM"
                              ? "text-yellow-300"
                              : "text-accent"
                        }`}
                      >
                        {risk}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div className="flex flex-wrap gap-4 border-t border-line px-4 py-3 text-xs text-muted">
              <span>Scanned: {marketScan.scanned}</span>
              <span>Successful: {marketScan.successful}</span>
              <span>Failed: {marketScan.failed}</span>
              <span>
                Ranked opportunities: {marketScan.opportunities.length}
              </span>
            </div>
          </div>
        )}
      </div>

      {selectedOpportunity && (
        <MultiTimeframeDetail
          opportunity={selectedOpportunity}
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(360px,.8fr)_minmax(0,1.5fr)]">
        <div className="border border-line bg-panel">
          <div className="grid grid-cols-[1.2fr_.7fr_.6fr_32px] border-b border-line px-4 py-3 text-xs tracking-wider text-muted">
            <span>SYMBOL</span>
            <span>PRICE</span>
            <span>DAY</span>
            <span />
          </div>

          <div className="scrollbar max-h-[570px] overflow-y-auto">
            {watchlist.length === 0 ? (
              <p className="p-6 text-sm text-muted">
                Search the built-in NSE symbols or refresh
                the instrument master, then add a stock.
              </p>
            ) : (
              watchlist.map((item) => (
                <div
                  key={item.symbol}
                  className={`grid grid-cols-[1.2fr_.7fr_.6fr_32px] items-center px-4 py-4 ${
                    selected?.symbol === item.symbol
                      ? "bg-[#12301b]"
                      : "hover:bg-[#0f1e12]"
                  }`}
                >
                  <button
                    onClick={() => onSelect(item)}
                    className="text-left"
                  >
                    <b>{item.symbol}</b>
                    <span className="mt-1 block truncate text-xs text-muted">
                      {item.name}
                    </span>
                  </button>

                  <span>{money(item.last_price)}</span>

                  <span
                    className={
                      (item.change_percent || 0) >= 0
                        ? "text-accent"
                        : "text-red-400"
                    }
                  >
                    {item.change_percent == null
                      ? "—"
                      : `${
                          item.change_percent >= 0 ? "+" : ""
                        }${item.change_percent}%`}
                  </span>

                  <button
                    onClick={() =>
                      onRemove(item.symbol)
                    }
                    className="text-muted hover:text-red-400"
                    title={`Remove ${item.symbol}`}
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="min-w-0 border border-line bg-panel">
          <div className="flex items-start justify-between border-b border-line p-5">
            <div>
              <h2 className="text-xl font-semibold">
                {selected?.symbol || "Select a stock"}
              </h2>

              <p className="mt-1 text-sm text-muted">
                {selected?.name ||
                  "Your chart will appear here"}
              </p>
            </div>

            <div className="text-right">
              <strong className="text-xl text-accent">
                {money(selected?.last_price)}
              </strong>

              <p className="mt-1 text-xs text-muted">
                EMA 20 · Volume
              </p>
            </div>
          </div>

          <div className="flex gap-2 border-b border-line p-4">
            {["15s", "1m", "5m", "15m"].map(
              (option) => (
                <button
                  key={option}
                  onClick={() => onInterval(option)}
                  className={`px-3 py-1.5 text-sm ${
                    interval === option
                      ? "bg-accent font-bold text-black"
                      : "border border-line text-muted hover:text-white"
                  }`}
                >
                  {option}
                </button>
              ),
            )}
          </div>

          {candles.length ? (
            <StockChart data={candles} interval={interval} />
          ) : (
            <div className="grid h-[430px] place-items-center text-muted">
              Select a watched stock to load its chart.
            </div>
          )}
        </div>
      </div>
    </>
  );
}
