"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

type RadarInstrument = {
  exchange: string;
  symbol: string;
  name: string;
  token: string;
  kind: string;
};

type InstrumentPage = {
  items: RadarInstrument[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

type LiveStock = {
  symbol: string;
  ltp: number;
  volume?: number | null;
};

type RadarScanner = {
  symbol: string;
  signal: string;
  score: number;
  trend: string;

  analysis?: {
    confidence?: number;
  };

  execution?: {
    last_price?: number;
  };
};

type RadarTab =
  | "opportunities"
  | "volume"
  | "movers"
  | "all";

type Props = {
  apiBase: string;

  liveStocks: LiveStock[];

  scanners: Record<
    string,
    RadarScanner
  >;

  onOpenStock: (
    symbol: string
  ) => void;

  onAddToWatchlist: (
    item: RadarInstrument
  ) =>
    | void
    | Promise<void>;
};

function formatPrice(
  value:
    | number
    | null
    | undefined
) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return "—";
  }

  return `₹${value.toLocaleString(
    "en-IN",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  )}`;
}

function formatVolume(
  value:
    | number
    | null
    | undefined
) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return "—";
  }

  if (
    value >= 10_000_000
  ) {
    return `${(
      value / 10_000_000
    ).toFixed(2)}Cr`;
  }

  if (
    value >= 100_000
  ) {
    return `${(
      value / 100_000
    ).toFixed(2)}L`;
  }

  if (
    value >= 1_000
  ) {
    return `${(
      value / 1_000
    ).toFixed(1)}K`;
  }

  return String(
    Math.round(value)
  );
}

function signalClass(
  signal: string
) {
  const normalized =
    signal.toUpperCase();

  if (
    normalized === "BUY"
  ) {
    return (
      "border-emerald-500/30 " +
      "bg-emerald-500/10 " +
      "text-emerald-300"
    );
  }

  if (
    normalized === "SELL"
  ) {
    return (
      "border-red-500/30 " +
      "bg-red-500/10 " +
      "text-red-300"
    );
  }

  return (
    "border-amber-500/30 " +
    "bg-amber-500/10 " +
    "text-amber-200"
  );
}

export default function MarketRadarPanel({
  apiBase,
  liveStocks,
  scanners,
  onOpenStock,
  onAddToWatchlist,
}: Props) {

  const [
    activeTab,
    setActiveTab,
  ] =
    useState<RadarTab>(
      "opportunities"
    );

  const [
    instruments,
    setInstruments,
  ] =
    useState<RadarInstrument[]>(
      []
    );

  const [
    search,
    setSearch,
  ] =
    useState("");

  const [
    page,
    setPage,
  ] =
    useState(1);

  const [
    total,
    setTotal,
  ] =
    useState(0);

  const [
    pages,
    setPages,
  ] =
    useState(1);

  const [
    loading,
    setLoading,
  ] =
    useState(false);

  const [
    message,
    setMessage,
  ] =
    useState("");

  const [
    addingSymbol,
    setAddingSymbol,
  ] =
    useState("");

  const pageSize = 50;

  const liveBySymbol =
    useMemo(
      () => {
        const map =
          new Map<
            string,
            LiveStock
          >();

        liveStocks.forEach(
          (
            stock
          ) => {
            map.set(
              stock.symbol
                .toUpperCase(),
              stock
            );
          }
        );

        return map;
      },
      [
        liveStocks,
      ]
    );

  const opportunities =
    useMemo(
      () =>
        Object
          .values(
            scanners
          )
          .sort(
            (
              first,
              second
            ) =>
              (
                second.score ||
                0
              )
              -
              (
                first.score ||
                0
              )
          ),
      [
        scanners,
      ]
    );

  const volumeLeaders =
    useMemo(
      () =>
        [...liveStocks]
          .filter(
            (
              item
            ) =>
              typeof (
                item.volume
              ) ===
                "number"
          )
          .sort(
            (
              first,
              second
            ) =>
              (
                second.volume ||
                0
              )
              -
              (
                first.volume ||
                0
              )
          )
          .slice(
            0,
            25
          ),
      [
        liveStocks,
      ]
    );

  useEffect(
    () => {

      if (
        activeTab !==
          "all"
      ) {
        return;
      }

      let active =
        true;

      const timer =
        window.setTimeout(
          async () => {

            setLoading(
              true
            );

            setMessage(
              ""
            );

            try {

              const params =
                new URLSearchParams(
                  {
                    page:
                      String(
                        page
                      ),

                    page_size:
                      String(
                        pageSize
                      ),

                    kind:
                      "EQUITY",
                  }
                );

              if (
                search
                  .trim()
              ) {
                params.set(
                  "q",
                  search
                    .trim()
                );
              }

              const response =
                await fetch(
                  `${apiBase}/api/instruments?${params.toString()}`,
                  {
                    credentials:
                      "include",
                    cache:
                      "no-store",
                  }
                );

              if (
                !response.ok
              ) {
                throw new Error(
                  await response.text()
                );
              }

              const data:
                InstrumentPage =
                await response
                  .json();

              if (
                !active
              ) {
                return;
              }

              setInstruments(
                data.items
              );

              setTotal(
                data.total
              );

              setPages(
                Math.max(
                  1,
                  data.pages
                )
              );

            } catch (
              error
            ) {

              if (
                !active
              ) {
                return;
              }

              setMessage(
                error instanceof
                  Error
                  ? error.message
                  : "Unable to load instruments"
              );

              setInstruments(
                []
              );

            } finally {

              if (
                active
              ) {
                setLoading(
                  false
                );
              }

            }

          },
          250
        );

      return () => {
        active =
          false;

        window
          .clearTimeout(
            timer
          );
      };

    },
    [
      activeTab,
      apiBase,
      page,
      search,
    ]
  );

  useEffect(
    () => {
      setPage(
        1
      );
    },
    [
      search,
    ]
  );

  async function addStock(
    item:
      RadarInstrument
  ) {

    setAddingSymbol(
      item.symbol
    );

    try {

      await onAddToWatchlist(
        item
      );

    } finally {

      setAddingSymbol(
        ""
      );

    }
  }

  return (
    <section
      className="
        min-w-0
        space-y-5
      "
    >

      {/* HEADER */}

      <div
        className="
          flex
          flex-col
          gap-4
          rounded-xl
          border
          border-emerald-950
          bg-[#07100b]
          p-5
          lg:flex-row
          lg:items-center
          lg:justify-between
        "
      >

        <div>

          <div
            className="
              text-[11px]
              font-semibold
              tracking-[0.28em]
              text-emerald-400
            "
          >
            NEXUS MARKET INTELLIGENCE
          </div>

          <h2
            className="
              mt-2
              text-2xl
              font-semibold
              text-white
            "
          >
            Market Radar
          </h2>

          <p
            className="
              mt-1
              text-sm
              text-slate-400
            "
          >
            Discover signals,
            live activity and
            NSE instruments.
          </p>

        </div>

        <div
          className="
            rounded-lg
            border
            border-emerald-900
            bg-emerald-950/20
            px-4
            py-3
          "
        >

          <div
            className="
              text-[10px]
              tracking-[0.18em]
              text-slate-500
            "
          >
            NSE INSTRUMENTS
          </div>

          <div
            className="
              mt-1
              text-lg
              font-semibold
              text-emerald-300
            "
          >
            {
              activeTab ===
                "all"
                ? total.toLocaleString(
                    "en-IN"
                  )
                : "LIVE"
            }
          </div>

        </div>

      </div>


      {/* TABS */}

      <div
        className="
          flex
          flex-wrap
          gap-2
        "
      >

        {(
          [
            [
              "opportunities",
              "TOP OPPORTUNITIES",
            ],

            [
              "volume",
              "LIVE VOLUME",
            ],

            [
              "movers",
              "MOVERS",
            ],

            [
              "all",
              "ALL STOCKS",
            ],
          ] as [
            RadarTab,
            string
          ][]
        ).map(
          (
            [
              key,
              label,
            ]
          ) => (

            <button
              key={
                key
              }
              type="button"
              onClick={
                () =>
                  setActiveTab(
                    key
                  )
              }
              className={`
                rounded-lg
                border
                px-4
                py-2
                text-xs
                font-semibold
                tracking-wide
                transition
                ${
                  activeTab ===
                  key
                    ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                    : "border-slate-800 bg-[#08120c] text-slate-400 hover:border-emerald-900 hover:text-white"
                }
              `}
            >
              {
                label
              }
            </button>

          )
        )}

      </div>


      {/* TOP OPPORTUNITIES */}

      {activeTab ===
        "opportunities" && (

        <div
          className="
            overflow-hidden
            rounded-xl
            border
            border-slate-800
            bg-[#07100b]
          "
        >

          <div
            className="
              flex
              items-center
              justify-between
              border-b
              border-slate-800
              px-5
              py-4
            "
          >

            <div>

              <div
                className="
                  text-sm
                  font-semibold
                  text-white
                "
              >
                Top Opportunities
              </div>

              <div
                className="
                  mt-1
                  text-xs
                  text-slate-500
                "
              >
                Ranked from
                scanner results
                already available
                in NEXUS.
              </div>

            </div>

            <span
              className="
                text-xs
                text-slate-500
              "
            >
              {
                opportunities
                  .length
              } scanned
            </span>

          </div>

          {opportunities
            .length === 0 ? (

            <div
              className="
                px-5
                py-16
                text-center
                text-sm
                text-slate-500
              "
            >
              No scanner
              opportunities are
              available yet.
            </div>

          ) : (

            <div
              className="
                overflow-x-auto
              "
            >

              <table
                className="
                  w-full
                  min-w-[760px]
                  text-left
                  text-sm
                "
              >

                <thead>

                  <tr
                    className="
                      border-b
                      border-slate-800
                      text-[10px]
                      uppercase
                      tracking-[0.14em]
                      text-slate-500
                    "
                  >

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Symbol
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Price
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Signal
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Confidence
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Trend
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Score
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Action
                    </th>

                  </tr>

                </thead>

                <tbody>

                  {opportunities
                    .map(
                      (
                        scanner
                      ) => {

                        const live =
                          liveBySymbol
                            .get(
                              scanner.symbol
                                .toUpperCase()
                            );

                        const price =
                          live
                            ?.ltp ??
                          scanner
                            .execution
                            ?.last_price;

                        const confidence =
                          scanner
                            .analysis
                            ?.confidence;

                        return (

                          <tr
                            key={
                              scanner.symbol
                            }
                            className="
                              border-b
                              border-slate-900
                              transition
                              hover:bg-emerald-950/10
                            "
                          >

                            <td
                              className="
                                px-5
                                py-4
                              "
                            >

                              <button
                                type="button"
                                onClick={
                                  () =>
                                    onOpenStock(
                                      scanner.symbol
                                    )
                                }
                                className="
                                  font-semibold
                                  text-white
                                  hover:text-emerald-300
                                "
                              >
                                {
                                  scanner.symbol
                                }
                              </button>

                            </td>

                            <td
                              className="
                                px-5
                                py-4
                                font-medium
                                text-slate-200
                              "
                            >
                              {
                                formatPrice(
                                  price
                                )
                              }
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                              "
                            >

                              <span
                                className={`
                                  inline-flex
                                  rounded-md
                                  border
                                  px-2.5
                                  py-1
                                  text-xs
                                  font-semibold
                                  ${signalClass(
                                    scanner.signal
                                  )}
                                `}
                              >
                                {
                                  scanner
                                    .signal
                                }
                              </span>

                            </td>

                            <td
                              className="
                                px-5
                                py-4
                                text-slate-300
                              "
                            >
                              {
                                typeof confidence ===
                                "number"
                                  ? `${confidence}%`
                                  : "—"
                              }
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                                text-slate-300
                              "
                            >
                              {
                                scanner.trend ||
                                "—"
                              }
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                                font-semibold
                                text-emerald-300
                              "
                            >
                              {
                                scanner.score
                              }
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                              "
                            >

                              <button
                                type="button"
                                onClick={
                                  () =>
                                    onOpenStock(
                                      scanner.symbol
                                    )
                                }
                                className="
                                  rounded-md
                                  border
                                  border-emerald-900
                                  px-3
                                  py-1.5
                                  text-xs
                                  font-semibold
                                  text-emerald-300
                                  hover:border-emerald-500
                                  hover:bg-emerald-500/10
                                "
                              >
                                OPEN CHART
                              </button>

                            </td>

                          </tr>

                        );

                      }
                    )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      )}


      {/* LIVE VOLUME */}

      {activeTab ===
        "volume" && (

        <div
          className="
            overflow-hidden
            rounded-xl
            border
            border-slate-800
            bg-[#07100b]
          "
        >

          <div
            className="
              border-b
              border-slate-800
              px-5
              py-4
            "
          >

            <div
              className="
                text-sm
                font-semibold
                text-white
              "
            >
              Highest Live Volume
            </div>

            <div
              className="
                mt-1
                text-xs
                text-slate-500
              "
            >
              Uses only real
              live volume currently
              available to the app.
            </div>

          </div>

          {volumeLeaders
            .length === 0 ? (

            <div
              className="
                px-5
                py-16
                text-center
                text-sm
                text-slate-500
              "
            >
              Live volume data is
              not available yet.
            </div>

          ) : (

            <div
              className="
                overflow-x-auto
              "
            >

              <table
                className="
                  w-full
                  min-w-[620px]
                  text-left
                  text-sm
                "
              >

                <thead>

                  <tr
                    className="
                      border-b
                      border-slate-800
                      text-[10px]
                      uppercase
                      tracking-[0.14em]
                      text-slate-500
                    "
                  >

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Rank
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Symbol
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      LTP
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Volume
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Chart
                    </th>

                  </tr>

                </thead>

                <tbody>

                  {volumeLeaders
                    .map(
                      (
                        item,
                        index
                      ) => (

                        <tr
                          key={
                            item.symbol
                          }
                          className="
                            border-b
                            border-slate-900
                            hover:bg-emerald-950/10
                          "
                        >

                          <td
                            className="
                              px-5
                              py-4
                              text-slate-500
                            "
                          >
                            #
                            {
                              index +
                              1
                            }
                          </td>

                          <td
                            className="
                              px-5
                              py-4
                            "
                          >

                            <button
                              type="button"
                              onClick={
                                () =>
                                  onOpenStock(
                                    item.symbol
                                  )
                              }
                              className="
                                font-semibold
                                text-white
                                hover:text-emerald-300
                              "
                            >
                              {
                                item.symbol
                              }
                            </button>

                          </td>

                          <td
                            className="
                              px-5
                              py-4
                              text-slate-200
                            "
                          >
                            {
                              formatPrice(
                                item.ltp
                              )
                            }
                          </td>

                          <td
                            className="
                              px-5
                              py-4
                              font-semibold
                              text-emerald-300
                            "
                          >
                            {
                              formatVolume(
                                item.volume
                              )
                            }
                          </td>

                          <td
                            className="
                              px-5
                              py-4
                            "
                          >

                            <button
                              type="button"
                              onClick={
                                () =>
                                  onOpenStock(
                                    item.symbol
                                  )
                              }
                              className="
                                text-xs
                                font-semibold
                                text-emerald-300
                                hover:text-emerald-200
                              "
                            >
                              OPEN →
                            </button>

                          </td>

                        </tr>

                      )
                    )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      )}


      {/* MOVERS */}

      {activeTab ===
        "movers" && (

        <div
          className="
            rounded-xl
            border
            border-slate-800
            bg-[#07100b]
            px-6
            py-16
            text-center
          "
        >

          <div
            className="
              mx-auto
              flex
              h-12
              w-12
              items-center
              justify-center
              rounded-full
              border
              border-emerald-900
              bg-emerald-950/20
              text-xl
              text-emerald-300
            "
          >
            ↕
          </div>

          <h3
            className="
              mt-4
              text-base
              font-semibold
              text-white
            "
          >
            Market Movers
          </h3>

          <p
            className="
              mx-auto
              mt-2
              max-w-lg
              text-sm
              leading-6
              text-slate-500
            "
          >
            Top gainers and
            losers will appear
            here after we add
            reliable previous-close
            data to the live feed.
            NEXUS will not fabricate
            change percentages.
          </p>

        </div>

      )}


      {/* ALL STOCKS */}

      {activeTab ===
        "all" && (

        <div
          className="
            overflow-hidden
            rounded-xl
            border
            border-slate-800
            bg-[#07100b]
          "
        >

          <div
            className="
              flex
              flex-col
              gap-4
              border-b
              border-slate-800
              px-5
              py-4
              md:flex-row
              md:items-center
              md:justify-between
            "
          >

            <div>

              <div
                className="
                  text-sm
                  font-semibold
                  text-white
                "
              >
                All NSE Stocks
              </div>

              <div
                className="
                  mt-1
                  text-xs
                  text-slate-500
                "
              >
                {
                  total.toLocaleString(
                    "en-IN"
                  )
                } instruments
              </div>

            </div>

            <div
              className="
                relative
                w-full
                md:w-80
              "
            >

              <input
                value={
                  search
                }
                onChange={
                  (
                    event
                  ) =>
                    setSearch(
                      event
                        .target
                        .value
                    )
                }
                placeholder="Search symbol or company..."
                className="
                  w-full
                  rounded-lg
                  border
                  border-slate-800
                  bg-[#050b07]
                  px-4
                  py-2.5
                  text-sm
                  text-white
                  outline-none
                  placeholder:text-slate-600
                  focus:border-emerald-600
                "
              />

            </div>

          </div>

          {message && (

            <div
              className="
                border-b
                border-red-950
                bg-red-950/20
                px-5
                py-3
                text-sm
                text-red-300
              "
            >
              {
                message
              }
            </div>

          )}

          {loading ? (

            <div
              className="
                flex
                min-h-[360px]
                items-center
                justify-center
              "
            >

              <div
                className="
                  h-8
                  w-8
                  animate-spin
                  rounded-full
                  border-2
                  border-emerald-950
                  border-r-emerald-400
                  border-t-emerald-400
                "
              />

            </div>

          ) : (

            <div
              className="
                overflow-x-auto
              "
            >

              <table
                className="
                  w-full
                  min-w-[900px]
                  text-left
                  text-sm
                "
              >

                <thead>

                  <tr
                    className="
                      border-b
                      border-slate-800
                      text-[10px]
                      uppercase
                      tracking-[0.14em]
                      text-slate-500
                    "
                  >

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Symbol
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Company
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Type
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      LTP
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Volume
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Watchlist
                    </th>

                    <th
                      className="
                        px-5
                        py-3
                      "
                    >
                      Chart
                    </th>

                  </tr>

                </thead>

                <tbody>

                  {instruments
                    .map(
                      (
                        item
                      ) => {

                        const live =
                          liveBySymbol
                            .get(
                              item.symbol
                                .toUpperCase()
                            );

                        return (

                          <tr
                            key={
                              item.token
                            }
                            className="
                              border-b
                              border-slate-900
                              transition
                              hover:bg-emerald-950/10
                            "
                          >

                            <td
                              className="
                                px-5
                                py-4
                              "
                            >

                              <button
                                type="button"
                                onClick={
                                  () =>
                                    onOpenStock(
                                      item.symbol
                                    )
                                }
                                className="
                                  font-semibold
                                  text-white
                                  hover:text-emerald-300
                                "
                              >
                                {
                                  item.symbol
                                }
                              </button>

                            </td>

                            <td
                              className="
                                max-w-[280px]
                                truncate
                                px-5
                                py-4
                                text-slate-400
                              "
                            >
                              {
                                item.name
                              }
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                              "
                            >
                              <span
                                className="
                                  rounded
                                  border
                                  border-slate-800
                                  bg-slate-900/40
                                  px-2
                                  py-1
                                  text-[10px]
                                  text-slate-400
                                "
                              >
                                {
                                  item.kind
                                }
                              </span>
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                                font-medium
                                text-slate-200
                              "
                            >
                              {
                                formatPrice(
                                  live?.ltp
                                )
                              }
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                                text-slate-400
                              "
                            >
                              {
                                formatVolume(
                                  live
                                    ?.volume
                                )
                              }
                            </td>

                            <td
                              className="
                                px-5
                                py-4
                              "
                            >

                              <button
                                type="button"
                                disabled={
                                  addingSymbol ===
                                  item.symbol
                                }
                                onClick={
                                  () =>
                                    void addStock(
                                      item
                                    )
                                }
                                className="
                                  rounded-md
                                  border
                                  border-slate-700
                                  px-3
                                  py-1.5
                                  text-xs
                                  font-semibold
                                  text-slate-300
                                  hover:border-emerald-600
                                  hover:text-emerald-300
                                  disabled:opacity-40
                                "
                              >
                                {
                                  addingSymbol ===
                                  item.symbol
                                    ? "ADDING..."
                                    : "+ WATCH"
                                }
                              </button>

                            </td>

                            <td
                              className="
                                px-5
                                py-4
                              "
                            >

                              <button
                                type="button"
                                onClick={
                                  () =>
                                    onOpenStock(
                                      item.symbol
                                    )
                                }
                                className="
                                  rounded-md
                                  border
                                  border-emerald-900
                                  px-3
                                  py-1.5
                                  text-xs
                                  font-semibold
                                  text-emerald-300
                                  hover:border-emerald-500
                                  hover:bg-emerald-500/10
                                "
                              >
                                OPEN
                              </button>

                            </td>

                          </tr>

                        );

                      }
                    )}

                </tbody>

              </table>

            </div>

          )}

          <div
            className="
              flex
              flex-col
              gap-3
              border-t
              border-slate-800
              px-5
              py-4
              sm:flex-row
              sm:items-center
              sm:justify-between
            "
          >

            <div
              className="
                text-xs
                text-slate-500
              "
            >
              Page {
                page
              } of {
                pages
              }
            </div>

            <div
              className="
                flex
                gap-2
              "
            >

              <button
                type="button"
                disabled={
                  page <= 1 ||
                  loading
                }
                onClick={
                  () =>
                    setPage(
                      (
                        current
                      ) =>
                        Math.max(
                          1,
                          current -
                            1
                        )
                    )
                }
                className="
                  rounded-md
                  border
                  border-slate-800
                  px-4
                  py-2
                  text-xs
                  font-semibold
                  text-slate-400
                  hover:border-emerald-800
                  hover:text-white
                  disabled:opacity-30
                "
              >
                ← PREVIOUS
              </button>

              <button
                type="button"
                disabled={
                  page >=
                    pages ||
                  loading
                }
                onClick={
                  () =>
                    setPage(
                      (
                        current
                      ) =>
                        Math.min(
                          pages,
                          current +
                            1
                        )
                    )
                }
                className="
                  rounded-md
                  border
                  border-slate-800
                  px-4
                  py-2
                  text-xs
                  font-semibold
                  text-slate-400
                  hover:border-emerald-800
                  hover:text-white
                  disabled:opacity-30
                "
              >
                NEXT →
              </button>

            </div>

          </div>

        </div>

      )}

    </section>
  );
}