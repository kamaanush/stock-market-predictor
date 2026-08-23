"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";


// ==================================================
// TYPES
// ==================================================

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
  | "movers"
  | "volume"
  | "all";


type Props = {
  apiBase: string;

  liveStocks: LiveStock[];
  trackedSymbols: string[];

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


// ==================================================
// HELPERS
// ==================================================

function formatPrice(
  value:
    | number
    | null
    | undefined
) {

  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(
      value
    )
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
    !Number.isFinite(
      value
    )
  ) {
    return "—";
  }


  if (
    value >=
    10_000_000
  ) {

    return `${(
      value /
      10_000_000
    ).toFixed(
      2
    )}Cr`;

  }


  if (
    value >=
    100_000
  ) {

    return `${(
      value /
      100_000
    ).toFixed(
      2
    )}L`;

  }


  if (
    value >=
    1_000
  ) {

    return `${(
      value /
      1_000
    ).toFixed(
      1
    )}K`;

  }


  return String(
    Math.round(
      value
    )
  );
}


function signalClass(
  signal: string
) {

  const normalized =
    signal
      .trim()
      .toUpperCase();


  if (
    normalized ===
    "BUY"
  ) {

    return (
      "border-emerald-500/30 " +
      "bg-emerald-500/10 " +
      "text-emerald-300"
    );

  }


  if (
    normalized ===
    "SELL"
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


// ==================================================
// COMPONENT
// ==================================================

export default function MarketRadarPanel({
  apiBase,
  liveStocks,
  trackedSymbols,
  scanners,
  onOpenStock,
  onAddToWatchlist,
}: Props) {


  // ==================================================
  // STATE
  // ==================================================

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
    useState<
      RadarInstrument[]
    >([]);


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


  const pageSize =
    50;


  // ==================================================
  // TRACKED STOCK LOOKUP
  // ==================================================

  const trackedSet =
    useMemo(
      () =>
        new Set(
          trackedSymbols.map(
            (
              symbol
            ) =>
              symbol
                .trim()
                .toUpperCase()
          )
        ),
      [
        trackedSymbols,
      ]
    );


  // ==================================================
  // LIVE STOCK LOOKUP
  // ==================================================

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
                .trim()
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


  // ==================================================
  // TOP OPPORTUNITIES
  // ==================================================

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


  // ==================================================
  // LIVE VOLUME LEADERS
  // ==================================================

  const volumeLeaders =
    useMemo(
      () =>
        [
          ...liveStocks,
        ]
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


  // ==================================================
  // RESET PAGE WHEN SEARCH CHANGES
  // ==================================================

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


  // ==================================================
  // LOAD NSE UNIVERSE
  // ==================================================

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


              const normalizedSearch =
                search
                  .trim();


              if (
                normalizedSearch
              ) {

                params.set(
                  "q",
                  normalizedSearch
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

                const body =
                  await response
                    .text();


                throw new Error(
                  body ||
                  "Unable to load NSE instruments"
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

                  : "Unable to load NSE instruments"
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


        window.clearTimeout(
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


  // ==================================================
  // ADD STOCK TO WATCHLIST
  // ==================================================

  async function addStock(
    item:
      RadarInstrument
  ) {

    const normalized =
      item.symbol
        .trim()
        .toUpperCase();


    if (
      trackedSet.has(
        normalized
      )
    ) {
      return;
    }


    setAddingSymbol(
      item.symbol
    );


    try {

      await onAddToWatchlist(
        item
      );


    } catch (
      error
    ) {

      console.error(
        `Could not add ${item.symbol} to watchlist`,
        error
      );


    } finally {

      setAddingSymbol(
        ""
      );

    }

  }


  // ==================================================
  // TABS
  // ==================================================

  const tabs:
    Array<[
      RadarTab,
      string
    ]> = [

      [
        "opportunities",
        "TOP OPPORTUNITIES",
      ],

      [
        "movers",
        "TOP MOVERS",
      ],

      [
        "volume",
        "LIVE VOLUME",
      ],

      [
        "all",
        "NSE UNIVERSE",
      ],

    ];


  // ==================================================
  // RENDER
  // ==================================================

  return (

    <section
      className="
        min-w-0
        space-y-5
      "
    >


      {/* ==================================================
          HEADER
      ================================================== */}

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
            Discover stocks,
            analyze tracked opportunities
            and monitor live NSE activity.
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
            {
              activeTab ===
              "all"

                ? "NSE UNIVERSE"

                : "MARKET STATUS"
            }
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


      {/* ==================================================
          TABS
      ================================================== */}

      <div
        className="
          flex
          flex-wrap
          gap-2
        "
      >

        {
          tabs.map(
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
          )
        }

      </div>


      {/* ==================================================
          TOP OPPORTUNITIES
      ================================================== */}

      {
        activeTab ===
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
                  Ranked from AI Scanner
                  results for your tracked
                  stocks.
                </div>

              </div>


              <span
                className="
                  text-xs
                  text-slate-500
                "
              >
                {
                  opportunities.length
                } scanned
              </span>

            </div>


            {
              opportunities.length ===
              0 ? (

                <div
                  className="
                    px-5
                    py-16
                    text-center
                    text-sm
                    text-slate-500
                  "
                >
                  No scanner results
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

                        <th className="px-5 py-3">
                          Symbol
                        </th>

                        <th className="px-5 py-3">
                          Price
                        </th>

                        <th className="px-5 py-3">
                          Signal
                        </th>

                        <th className="px-5 py-3">
                          Confidence
                        </th>

                        <th className="px-5 py-3">
                          Trend
                        </th>

                        <th className="px-5 py-3">
                          Score
                        </th>

                      </tr>

                    </thead>


                    <tbody>

                      {
                        opportunities.map(
                          (
                            scanner
                          ) => {

                            const symbol =
                              scanner.symbol
                                .trim()
                                .toUpperCase();


                            const live =
                              liveBySymbol.get(
                                symbol
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
                                  symbol
                                }

                                onClick={
                                  () =>
                                    onOpenStock(
                                      symbol
                                    )
                                }

                                className="
                                  cursor-pointer
                                  border-b
                                  border-slate-900
                                  transition
                                  hover:bg-emerald-950/20
                                "
                              >

                                <td
                                  className="
                                    px-5
                                    py-4
                                    font-semibold
                                    text-white
                                  "
                                >
                                  {
                                    symbol
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

                                      ${
                                        signalClass(
                                          scanner.signal
                                        )
                                      }
                                    `}
                                  >
                                    {
                                      scanner.signal
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
                                    text-cyan-300
                                  "
                                >
                                  {
                                    scanner.score ??
                                    "—"
                                  }
                                </td>

                              </tr>

                            );

                          }
                        )
                      }

                    </tbody>

                  </table>

                </div>

              )
            }

          </div>

        )
      }


      {/* ==================================================
          TOP MOVERS
      ================================================== */}

      {
        activeTab ===
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
                text-lg
                font-semibold
                text-white
              "
            >
              Top Movers
            </div>


            <div
              className="
                mx-auto
                mt-3
                max-w-xl
                text-sm
                leading-6
                text-slate-500
              "
            >
              Real gainers and losers
              require previous-close data.
              We will connect this only
              when genuine market change
              percentage is available.
            </div>

          </div>

        )
      }


      {/* ==================================================
          LIVE VOLUME
      ================================================== */}

      {
        activeTab ===
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
                Live Volume
              </div>


              <div
                className="
                  mt-1
                  text-xs
                  text-slate-500
                "
              >
                Tracked stocks ranked
                by current live market
                volume.
              </div>

            </div>


            {
              volumeLeaders.length ===
              0 ? (

                <div
                  className="
                    px-5
                    py-16
                    text-center
                    text-sm
                    text-slate-500
                  "
                >
                  Waiting for live
                  volume data.
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

                        <th className="px-5 py-3">
                          Rank
                        </th>

                        <th className="px-5 py-3">
                          Symbol
                        </th>

                        <th className="px-5 py-3">
                          Price
                        </th>

                        <th className="px-5 py-3">
                          Volume
                        </th>

                        <th className="px-5 py-3">
                          Signal
                        </th>

                      </tr>

                    </thead>


                    <tbody>

                      {
                        volumeLeaders.map(
                          (
                            item,
                            index
                          ) => {

                            const symbol =
                              item.symbol
                                .trim()
                                .toUpperCase();


                            const scanner =
                              scanners[
                                symbol
                              ];


                            return (

                              <tr
                                key={
                                  symbol
                                }

                                onClick={
                                  () =>
                                    onOpenStock(
                                      symbol
                                    )
                                }

                                className="
                                  cursor-pointer
                                  border-b
                                  border-slate-900
                                  transition
                                  hover:bg-emerald-950/20
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
                                    font-semibold
                                    text-white
                                  "
                                >
                                  {
                                    symbol
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
                                    text-cyan-300
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

                                  {
                                    scanner ? (

                                      <span
                                        className={`
                                          inline-flex
                                          rounded-md
                                          border
                                          px-2.5
                                          py-1
                                          text-xs
                                          font-semibold

                                          ${
                                            signalClass(
                                              scanner.signal
                                            )
                                          }
                                        `}
                                      >
                                        {
                                          scanner.signal
                                        }
                                      </span>

                                    ) : (

                                      <span
                                        className="
                                          text-slate-600
                                        "
                                      >
                                        —
                                      </span>

                                    )
                                  }

                                </td>

                              </tr>

                            );

                          }
                        )
                      }

                    </tbody>

                  </table>

                </div>

              )
            }

          </div>

        )
      }


      {/* ==================================================
          NSE UNIVERSE
      ================================================== */}

      {
        activeTab ===
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

            {/* UNIVERSE HEADER */}

            <div
              className="
                flex
                flex-col
                gap-4
                border-b
                border-slate-800
                px-5
                py-4
                lg:flex-row
                lg:items-center
                lg:justify-between
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
                  NSE Universe
                </div>


                <div
                  className="
                    mt-1
                    text-xs
                    text-slate-500
                  "
                >
                  Search any NSE company.
                  Track only stocks you
                  want NEXUS to monitor
                  and scan.
                </div>

              </div>


              <div
                className="
                  flex
                  items-center
                  gap-3
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
                        event.target.value
                      )
                  }

                  placeholder="Search symbol or company"

                  className="
                    min-w-[260px]
                    rounded-lg
                    border
                    border-slate-800
                    bg-[#040b07]
                    px-4
                    py-2.5
                    text-sm
                    text-white
                    outline-none
                    transition
                    placeholder:text-slate-600
                    focus:border-emerald-700
                  "
                />

              </div>

            </div>


            {/* MESSAGE */}

            {
              message && (

                <div
                  className="
                    border-b
                    border-red-950
                    bg-red-950/20
                    px-5
                    py-3
                    text-xs
                    text-red-300
                  "
                >
                  {
                    message
                  }
                </div>

              )
            }


            {/* LOADING */}

            {
              loading ? (

                <div
                  className="
                    px-5
                    py-16
                    text-center
                    text-sm
                    text-slate-500
                  "
                >
                  Loading NSE
                  instruments...
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
                      min-w-[820px]
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

                        <th className="px-5 py-3">
                          Symbol
                        </th>

                        <th className="px-5 py-3">
                          Company
                        </th>

                        <th className="px-5 py-3">
                          Status
                        </th>

                        <th className="px-5 py-3">
                          Signal
                        </th>

                        <th className="px-5 py-3">
                          Action
                        </th>

                      </tr>

                    </thead>


                    <tbody>

                      {
                        instruments.map(
                          (
                            item
                          ) => {

                            const symbol =
                              item.symbol
                                .trim()
                                .toUpperCase();


                            const tracked =
                              trackedSet.has(
                                symbol
                              );


                            const scanner =
                              scanners[
                                symbol
                              ];


                            return (

                              <tr
                                key={`${item.exchange}-${item.token}-${item.symbol}`}

                                onClick={
                                  () =>
                                    onOpenStock(
                                      symbol
                                    )
                                }

                                className="
                                  cursor-pointer
                                  border-b
                                  border-slate-900
                                  transition
                                  hover:bg-emerald-950/20
                                "
                              >

                                {/* SYMBOL */}

                                <td
                                  className="
                                    px-5
                                    py-4
                                  "
                                >

                                  <span
                                    className="
                                      font-semibold
                                      text-white
                                    "
                                  >
                                    {
                                      symbol
                                    }
                                  </span>

                                </td>


                                {/* COMPANY */}

                                <td
                                  className="
                                    max-w-[340px]
                                    px-5
                                    py-4
                                    text-slate-400
                                  "
                                >
                                  {
                                    item.name ||
                                    "—"
                                  }
                                </td>


                                {/* STATUS */}

                                <td
                                  className="
                                    px-5
                                    py-4
                                  "
                                >

                                  {
                                    tracked ? (

                                      <span
                                        className="
                                          inline-flex
                                          rounded-md
                                          border
                                          border-emerald-500/30
                                          bg-emerald-500/10
                                          px-2.5
                                          py-1
                                          text-[10px]
                                          font-semibold
                                          tracking-wide
                                          text-emerald-300
                                        "
                                      >
                                        TRACKED
                                      </span>

                                    ) : (

                                      <span
                                        className="
                                          inline-flex
                                          rounded-md
                                          border
                                          border-slate-700
                                          bg-slate-900/30
                                          px-2.5
                                          py-1
                                          text-[10px]
                                          font-semibold
                                          tracking-wide
                                          text-slate-500
                                        "
                                      >
                                        NOT TRACKED
                                      </span>

                                    )
                                  }

                                </td>


                                {/* SIGNAL */}

                                <td
                                  className="
                                    px-5
                                    py-4
                                  "
                                >

                                  {
                                    scanner ? (

                                      <span
                                        className={`
                                          inline-flex
                                          rounded-md
                                          border
                                          px-2.5
                                          py-1
                                          text-xs
                                          font-semibold

                                          ${
                                            signalClass(
                                              scanner.signal
                                            )
                                          }
                                        `}
                                      >
                                        {
                                          scanner.signal
                                        }
                                      </span>

                                    ) : tracked ? (

                                      <span
                                        className="
                                          text-xs
                                          font-semibold
                                          text-cyan-400
                                        "
                                      >
                                        PENDING
                                      </span>

                                    ) : (

                                      <span
                                        className="
                                          text-slate-600
                                        "
                                      >
                                        —
                                      </span>

                                    )
                                  }

                                </td>


                                {/* ACTION */}

                                <td
                                  className="
                                    px-5
                                    py-4
                                  "
                                >

                                  {
                                    tracked ? (

                                      <span
                                        className="
                                          text-xs
                                          font-semibold
                                          text-emerald-400
                                        "
                                      >
                                        ✓ TRACKED
                                      </span>

                                    ) : (

                                      <button
                                        type="button"

                                        disabled={
                                          addingSymbol ===
                                          item.symbol
                                        }

                                        onClick={
                                          (
                                            event
                                          ) => {

                                            event
                                              .stopPropagation();


                                            void addStock(
                                              item
                                            );

                                          }
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
                                          transition
                                          hover:border-emerald-500
                                          hover:bg-emerald-500/10
                                          hover:text-emerald-300
                                          disabled:cursor-not-allowed
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

                                    )
                                  }

                                </td>

                              </tr>

                            );

                          }
                        )
                      }


                      {
                        instruments.length ===
                        0 && (

                          <tr>

                            <td
                              colSpan={
                                5
                              }

                              className="
                                px-5
                                py-16
                                text-center
                                text-sm
                                text-slate-500
                              "
                            >
                              No NSE stocks
                              found.
                            </td>

                          </tr>

                        )
                      }

                    </tbody>

                  </table>

                </div>

              )
            }


            {/* PAGINATION */}

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
                {
                  total.toLocaleString(
                    "en-IN"
                  )
                } NSE equity instruments
              </div>


              <div
                className="
                  flex
                  items-center
                  gap-3
                "
              >

                <button
                  type="button"

                  disabled={
                    page <=
                    1
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
                    px-3
                    py-1.5
                    text-xs
                    text-slate-300
                    disabled:cursor-not-allowed
                    disabled:opacity-30
                  "
                >
                  PREVIOUS
                </button>


                <span
                  className="
                    text-xs
                    text-slate-500
                  "
                >
                  PAGE{" "}
                  {
                    page
                  }{" "}
                  /{" "}
                  {
                    pages
                  }
                </span>


                <button
                  type="button"

                  disabled={
                    page >=
                    pages
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
                    px-3
                    py-1.5
                    text-xs
                    text-slate-300
                    disabled:cursor-not-allowed
                    disabled:opacity-30
                  "
                >
                  NEXT
                </button>

              </div>

            </div>

          </div>

        )
      }

    </section>

  );
}