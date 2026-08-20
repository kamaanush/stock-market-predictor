import {
  expect,
  test,
} from "@playwright/test";


test.setTimeout(
  90_000
);


const ICICI = {
  exchange: "NSE",
  symbol: "ICICIBANK",
  name: "ICICI Bank Ltd",
  token: "4963",
  kind: "EQUITY",
};


const RELIANCE = {
  exchange: "NSE",
  symbol: "RELIANCE",
  name: "Reliance Industries Ltd",
  token: "2885",
  kind: "EQUITY",
};


// ==================================================
// MOCK SCANNER RESULT
// ==================================================

function scannerResult(
  symbol: string,
  price: number
) {

  return {
    symbol,

    signal:
      "BUY",

    score:
      82,

    grade:
      "A",

    trend:
      "BULLISH",

    reason:
      "Strong automated test signal",

    technical_analysis: {

      ema:
        "BULLISH",

      ema_fast:
        price - 3,

      ema_slow:
        price - 8,

      supertrend:
        "BULLISH",

      supertrend_value:
        price - 10,

      adx:
        28,

      plus_di:
        32,

      minus_di:
        18,

      trend_strength:
        "STRONG",

      rsi:
        61,

      macd:
        "BULLISH",

      macd_value:
        4.2,

      macd_signal:
        3.1,

      vwap:
        "ABOVE",

      vwap_value:
        price - 5,

      volume:
        "HIGH",

      volume_value:
        2_500_000,

      average_volume:
        1_800_000,

      atr:
        12.5,

      pattern:
        null,

      pattern_direction:
        null,

      pattern_confidence:
        null,
    },

    cpr: {

      pivot:
        price,

      top_central:
        price + 2,

      bottom_central:
        price - 2,

      width:
        4,

      width_percent:
        0.3,

      classification:
        "NARROW",

      position:
        "ABOVE CPR",
    },

    trade_plan: {

      entry:
        price,

      stoploss:
        price - 20,

      target1:
        price + 30,

      target2:
        price + 50,

      risk_reward:
        "1:2",
    },

    analysis: {

      engine:
        "NEXUS TEST",

      confidence:
        86,

      probability_label:
        "HIGH",

      risk_label:
        "MEDIUM",

      summary:
        "Deterministic Playwright scanner response",
    },

    ai_analysis: {

      engine:
        "NEXUS TEST",

      market_bias:
        "BULLISH",

      trend_analysis:
        "Bullish automated test trend",

      momentum_analysis:
        "Positive automated test momentum",

      volume_analysis:
        "Healthy automated test volume",

      risk_analysis:
        "Controlled automated test risk",

      recommendation:
        "BUY",

      overall_summary:
        "Automated browser test result",
    },

    execution: {

      status:
        "READY",

      timeframe:
        "15m",

      last_price:
        price,
    },
  };
}


// ==================================================
// MOCK CANDLE RESPONSE
// ==================================================

function candleResponse(
  symbol: string
) {

  const candles = [
    {
      time:
        1787206500,

      open:
        1410,

      high:
        1425,

      low:
        1405,

      close:
        1420,

      volume:
        100000,
    },

    {
      time:
        1787207400,

      open:
        1420,

      high:
        1435,

      low:
        1418,

      close:
        1430,

      volume:
        120000,
    },

    {
      time:
        1787208300,

      open:
        1430,

      high:
        1440,

      low:
        1422,

      close:
        1435,

      volume:
        140000,
    },

    {
      time:
        1787209200,

      open:
        1435,

      high:
        1448,

      low:
        1431,

      close:
        1442,

      volume:
        155000,
    },

    {
      time:
        1787210100,

      open:
        1442,

      high:
        1450,

      low:
        1438,

      close:
        1446,

      volume:
        170000,
    },
  ];


  return {

    symbol,

    "15s":
      candles,

    "1m":
      candles,

    "5m":
      candles,

    "15m":
      candles,

    "1D":
      candles,

    "1W":
      candles,

    "1M":
      candles,
  };
}


// ==================================================
// MAIN TEST
// ==================================================

test(
  "NEXUS Market Radar to Watchlist workflow",
  async ({
    page,
  }) => {

    // ==================================================
    // FAKE DATABASE STATE
    // ==================================================

    const trackedSymbols =
      new Set<string>([
        "RELIANCE",
      ]);


    const scannerCalls =
      new Set<string>();


    // ==================================================
    // MOCK WEBSOCKET
    // ==================================================

    await page.addInitScript(
      () => {

        const testWindow =
          window as typeof window & {
            __NEXUS_E2E_TRACKED__?:
              string[];
          };


        testWindow
          .__NEXUS_E2E_TRACKED__ = [
            "RELIANCE",
          ];


        class MockWebSocket {

          static CONNECTING =
            0;

          static OPEN =
            1;

          static CLOSING =
            2;

          static CLOSED =
            3;


          CONNECTING =
            0;

          OPEN =
            1;

          CLOSING =
            2;

          CLOSED =
            3;


          readyState =
            MockWebSocket.CONNECTING;


          url:
            string;


          onopen:
            ((
              event: Event
            ) => void)
            | null =
            null;


          onmessage:
            ((
              event:
                MessageEvent
            ) => void)
            | null =
            null;


          onerror:
            ((
              event: Event
            ) => void)
            | null =
            null;


          onclose:
            ((
              event:
                CloseEvent
            ) => void)
            | null =
            null;


          constructor(
            url: string
          ) {

            this.url =
              url;


            window.setTimeout(
              () => {

                this.readyState =
                  MockWebSocket.OPEN;


                this.onopen?.(
                  new Event(
                    "open"
                  )
                );


                window.setTimeout(
                  () => {

                    const tracked =
                      testWindow
                        .__NEXUS_E2E_TRACKED__
                      ??
                      [
                        "RELIANCE",
                      ];


                    const stocks =
                      tracked.map(
                        (
                          symbol
                        ) => {

                          if (
                            symbol ===
                            "ICICIBANK"
                          ) {

                            return {

                              symbol:
                                "ICICIBANK",

                              token:
                                "4963",

                              ltp:
                                1435.25,

                              volume:
                                2_500_000,

                              exchange_timestamp:
                                Date.now(),

                              received_at:
                                new Date()
                                  .toISOString(),
                            };
                          }


                          return {

                            symbol:
                              "RELIANCE",

                            token:
                              "2885",

                            ltp:
                              1385.50,

                            volume:
                              3_500_000,

                            exchange_timestamp:
                              Date.now(),

                            received_at:
                              new Date()
                                .toISOString(),
                          };

                        }
                      );


                    this.onmessage?.(
                      new MessageEvent(
                        "message",
                        {
                          data:
                            JSON.stringify(
                              {

                                type:
                                  "market_update",

                                status:
                                  "live",

                                count:
                                  stocks.length,

                                time:
                                  new Date()
                                    .toISOString(),

                                stocks,
                              }
                            ),
                        }
                      )
                    );

                  },
                  50
                );

              },
              25
            );
          }


          send(
            _data?: string
          ) {

            // No-op for test.

          }


          close() {

            this.readyState =
              MockWebSocket.CLOSED;

          }
        }


        Object.defineProperty(
          window,
          "WebSocket",
          {

            configurable:
              true,

            writable:
              true,

            value:
              MockWebSocket,
          }
        );

      }
    );


    // ==================================================
    // MOCK BACKEND
    // ==================================================

    await page.route(
      "http://localhost:8000/api/**",
      async (
        route
      ) => {

        const request =
          route.request();


        const url =
          new URL(
            request.url()
          );


        const path =
          url.pathname;


        const method =
          request.method();


        // ==================================================
        // AUTH
        // ==================================================

        if (
          path ===
          "/api/auth/login"
          &&
          method ===
          "POST"
        ) {

          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify({
                authenticated:
                  true,
              }),
          });


          return;
        }


        // ==================================================
        // PORTFOLIO
        // ==================================================

        if (
          path ===
          "/api/portfolio/holdings"
          &&
          method ===
          "GET"
        ) {

          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                []
              ),
          });


          return;
        }


        // ==================================================
        // ALERTS
        // ==================================================

        if (
          path ===
          "/api/alerts"
          &&
          method ===
          "GET"
        ) {

          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                []
              ),
          });


          return;
        }


        if (
          path ===
          "/api/alerts/events"
          &&
          method ===
          "GET"
        ) {

          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                []
              ),
          });


          return;
        }


        // ==================================================
        // WATCHLIST SYMBOLS
        // ==================================================

        if (
          path ===
          "/api/watchlist/symbols"
          &&
          method ===
          "GET"
        ) {

          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                Array.from(
                  trackedSymbols
                )
              ),
          });


          return;
        }


        // ==================================================
        // GET WATCHLIST
        // ==================================================

        if (
          path ===
          "/api/watchlist"
          &&
          method ===
          "GET"
        ) {

          const items =
            Array
              .from(
                trackedSymbols
              )
              .map(
                (
                  symbol
                ) => {

                  if (
                    symbol ===
                    "ICICIBANK"
                  ) {

                    return {
                      ...ICICI,

                      last_price:
                        1435.25,

                      change_percent:
                        1.42,
                    };
                  }


                  return {
                    ...RELIANCE,

                    last_price:
                      1385.50,

                    change_percent:
                      0.85,
                  };

                }
              );


          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                items
              ),
          });


          return;
        }


        // ==================================================
        // ADD WATCHLIST
        // ==================================================

        if (
          path ===
          "/api/watchlist"
          &&
          method ===
          "POST"
        ) {

          const body =
            request
              .postDataJSON();


          const symbol =
            String(
              body.symbol
            )
              .trim()
              .toUpperCase();


          trackedSymbols.add(
            symbol
          );


          await route.fulfill({
            status:
              201,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                {

                  symbol,

                  name:
                    body.name,

                  token:
                    body.token,

                  kind:
                    body.kind,

                  last_price:
                    symbol ===
                    "ICICIBANK"
                      ? 1435.25
                      : 1385.50,

                  change_percent:
                    1.42,
                }
              ),
          });


          return;
        }


        // ==================================================
        // DELETE WATCHLIST
        // ==================================================

        if (
          path.startsWith(
            "/api/watchlist/"
          )
          &&
          method ===
          "DELETE"
        ) {

          const symbol =
            decodeURIComponent(
              path
                .split(
                  "/"
                )
                .pop()
              ??
              ""
            )
              .trim()
              .toUpperCase();


          trackedSymbols.delete(
            symbol
          );


          await route.fulfill({
            status:
              204,
          });


          return;
        }


        // ==================================================
        // NSE UNIVERSE
        // ==================================================

        if (
          path ===
          "/api/instruments"
          &&
          method ===
          "GET"
        ) {

          const search =
            (
              url
                .searchParams
                .get(
                  "q"
                )
              ??
              ""
            )
              .trim()
              .toUpperCase();


          const universe =
            [
              RELIANCE,
              ICICI,
            ];


          const items =
            search

              ? universe.filter(
                  (
                    item
                  ) =>

                    item.symbol
                      .toUpperCase()
                      .includes(
                        search
                      )

                    ||

                    item.name
                      .toUpperCase()
                      .includes(
                        search
                      )
                )

              : universe;


          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                {

                  items,

                  page:
                    1,

                  page_size:
                    50,

                  total:
                    items.length,

                  pages:
                    1,
                }
              ),
          });


          return;
        }


        // ==================================================
        // GLOBAL SEARCH
        // ==================================================

        if (
          path ===
          "/api/instruments/search"
          &&
          method ===
          "GET"
        ) {

          const search =
            (
              url
                .searchParams
                .get(
                  "q"
                )
              ??
              ""
            )
              .trim()
              .toUpperCase();


          const items =
            [
              RELIANCE,
              ICICI,
            ].filter(
              (
                item
              ) =>

                item.symbol
                  .toUpperCase()
                  .includes(
                    search
                  )

                ||

                item.name
                  .toUpperCase()
                  .includes(
                    search
                  )
            );


          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                items
              ),
          });


          return;
        }


        // ==================================================
        // SCANNER
        // ==================================================

        if (
          path.startsWith(
            "/api/v2/scanner/"
          )
          &&
          method ===
          "GET"
        ) {

          const symbol =
            decodeURIComponent(
              path
                .split(
                  "/"
                )
                .pop()
              ??
              "RELIANCE"
            )
              .trim()
              .toUpperCase();


          scannerCalls.add(
            symbol
          );


          const price =
            symbol ===
            "ICICIBANK"
              ? 1435.25
              : 1385.50;


          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                scannerResult(
                  symbol,
                  price
                )
              ),
          });


          return;
        }


        // ==================================================
        // CANDLES
        // ==================================================

        if (
          path.includes(
            "/candles/"
          )
          &&
          method ===
          "GET"
        ) {

          const symbol =
            decodeURIComponent(
              path
                .split(
                  "/"
                )
                .pop()
              ??
              "ICICIBANK"
            )
              .trim()
              .toUpperCase();


          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                candleResponse(
                  symbol
                )
              ),
          });


          return;
        }


        // ==================================================
        // QUOTE
        // ==================================================

        if (
          path.includes(
            "quote"
          )
          &&
          method ===
          "GET"
        ) {

          await route.fulfill({
            status:
              200,

            contentType:
              "application/json",

            body:
              JSON.stringify(
                {

                  symbol:
                    "ICICIBANK",

                  last_price:
                    1435.25,

                  change_percent:
                    1.42,
                }
              ),
          });


          return;
        }


        // ==================================================
        // FALLBACK
        // ==================================================

        console.log(
          "[PLAYWRIGHT] Unhandled API:",
          method,
          path
        );


        await route.fulfill({
          status:
            200,

          contentType:
            "application/json",

          body:
            JSON.stringify(
              {}
            ),
        });

      }
    );


    // ==================================================
    // OPEN DASHBOARD
    // ==================================================

    await page.goto(
      "/dashboard",
      {
        waitUntil:
          "domcontentloaded",
      }
    );


    // ==================================================
    // VERIFY SIDEBAR
    // ==================================================

    const marketRadarNav =
      page
        .locator(
          "aside.sidebar button.nav-item"
        )
        .filter({
          hasText:
            "MARKET RADAR",
        });


    await expect(
      marketRadarNav
    ).toBeVisible({
      timeout:
        15_000,
    });


    // ==================================================
    // OPEN MARKET RADAR
    // ==================================================

    await marketRadarNav.click();


    // Verify actual Radar component loaded.

    await expect(
      page.getByText(
        "NEXUS MARKET INTELLIGENCE",
        {
          exact:
            true,
        }
      )
    ).toBeVisible({
      timeout:
        15_000,
    });


    // ==================================================
    // OPEN NSE UNIVERSE / ALL STOCKS
    // ==================================================

    const universeTab =
      page
        .locator(
          "button"
        )
        .filter({
          hasText:
            /NSE UNIVERSE|ALL STOCKS/i,
        })
        .first();


    await expect(
      universeTab
    ).toBeVisible({
      timeout:
        15_000,
    });


    await universeTab.click();


    // ==================================================
    // FIND UNIVERSE SEARCH
    // ==================================================

    const universeSearch =
      page.getByPlaceholder(
        /Search symbol or company/i
      );


    await expect(
      universeSearch
    ).toBeVisible({
      timeout:
        10_000,
    });


    // ==================================================
    // SEARCH ICICI
    // ==================================================

    await universeSearch.fill(
      "ICICIBANK"
    );


    const iciciUniverseRow =
      page
        .locator(
          "tbody tr"
        )
        .filter({
          hasText:
            "ICICIBANK",
        })
        .first();


    await expect(
      iciciUniverseRow
    ).toBeVisible({
      timeout:
        15_000,
    });


    await expect(
      iciciUniverseRow
    ).toContainText(
      "ICICI Bank"
    );


    // ==================================================
    // FIND WATCH BUTTON
    // ==================================================

    const addButton =
      iciciUniverseRow
        .getByRole(
          "button",
          {
            name:
              /\+ WATCH|ADDING/i,
          }
        );


    await expect(
      addButton
    ).toBeVisible();


    // ==================================================
    // PREPARE NEXT WEBSOCKET STATE
    // ==================================================

    await page.evaluate(
      () => {

        const testWindow =
          window as typeof window & {
            __NEXUS_E2E_TRACKED__?:
              string[];
          };


        testWindow
          .__NEXUS_E2E_TRACKED__ = [
            "RELIANCE",
            "ICICIBANK",
          ];

      }
    );


    // ==================================================
    // ADD ICICI TO WATCHLIST
    // ==================================================

    await addButton.click();


    // ==================================================
    // VERIFY MOCK DATABASE
    // ==================================================

    await expect
      .poll(
        () =>
          trackedSymbols.has(
            "ICICIBANK"
          ),
        {

          timeout:
            10_000,

          message:
            "ICICIBANK was not added to mocked Watchlist",
        }
      )
      .toBe(
        true
      );


    // ==================================================
    // VERIFY ICICI APPEARS IN UI
    // ==================================================

    await expect(
      page
        .getByText(
          "ICICIBANK",
          {
            exact:
              true,
          }
        )
        .first()
    ).toBeVisible({
      timeout:
        15_000,
    });


    // ==================================================
    // VERIFY SCANNER RECEIVES ICICI
    // ==================================================

    await expect
      .poll(
        () =>
          scannerCalls.has(
            "ICICIBANK"
          ),
        {

          timeout:
            30_000,

          intervals: [
            500,
            1000,
            1500,
            2500,
          ],

          message:
            "ICICIBANK was added but was not scanned",
        }
      )
      .toBe(
        true
      );


    // ==================================================
    // OPEN AI SCANNER
    // ==================================================

    const scannerNav =
      page
        .locator(
          "aside.sidebar button.nav-item"
        )
        .filter({
          hasText:
            "AI SCANNER",
        });


    await expect(
      scannerNav
    ).toBeVisible();


    await scannerNav.click();


    await expect(
      page
        .getByText(
          "ICICIBANK",
          {
            exact:
              true,
          }
        )
        .first()
    ).toBeVisible({
      timeout:
        15_000,
    });


    // ==================================================
    // RETURN TO MARKET RADAR
    // ==================================================

    const marketRadarNavAgain =
      page
        .locator(
          "aside.sidebar button.nav-item"
        )
        .filter({
          hasText:
            "MARKET RADAR",
        });


    await expect(
      marketRadarNavAgain
    ).toBeVisible();


    await marketRadarNavAgain.click();


    // Verify Radar is actually active.

    await expect(
      page.getByText(
        "NEXUS MARKET INTELLIGENCE",
        {
          exact:
            true,
        }
      )
    ).toBeVisible({
      timeout:
        15_000,
    });


    // ==================================================
    // OPEN TOP OPPORTUNITIES
    // ==================================================

    const topOpportunitiesButton =
      page
        .locator(
          "button"
        )
        .filter({
          hasText:
            "TOP OPPORTUNITIES",
        })
        .first();


    await expect(
      topOpportunitiesButton
    ).toBeVisible({
      timeout:
        15_000,
    });


    await topOpportunitiesButton.click();


    // ==================================================
    // FIND ICICI BUY OPPORTUNITY
    // ==================================================

    const opportunityRow =
      page
        .locator(
          "tbody tr"
        )
        .filter({
          hasText:
            "ICICIBANK",
        })
        .filter({
          hasText:
            "BUY",
        })
        .first();


    await expect(
      opportunityRow
    ).toBeVisible({
      timeout:
        20_000,
    });


    await expect(
      opportunityRow
    ).toContainText(
      "ICICIBANK"
    );


    await expect(
      opportunityRow
    ).toContainText(
      "BUY"
    );


    // ==================================================
    // OPEN FULLSCREEN CHART
    // ==================================================

    const openChartButton =
      opportunityRow
        .getByRole(
          "button",
          {
            name:
              /OPEN CHART|OPEN/i,
          }
        )
        .last();


    await expect(
      openChartButton
    ).toBeVisible();


    await openChartButton.click();


    // ==================================================
    // VERIFY FULLSCREEN CHART
    // ==================================================

    const liveChartLabel =
      page.getByText(
        "NSE • LIVE CHART",
        {
          exact:
            true,
        }
      );


    await expect(
      liveChartLabel
    ).toBeVisible({
      timeout:
        15_000,
    });


    await expect(
      page
        .getByText(
          "ICICIBANK",
          {
            exact:
              true,
          }
        )
        .first()
    ).toBeVisible();


    // ==================================================
    // CHANGE TIMEFRAME
    // ==================================================

    const fiveMinuteButton =
      page
        .getByRole(
          "button",
          {
            name:
              "5m",

            exact:
              true,
          }
        )
        .last();


    await expect(
      fiveMinuteButton
    ).toBeVisible();


    await fiveMinuteButton.click();


    // ==================================================
    // VERIFY CHART REMAINS OPEN
    // ==================================================

    await expect(
      liveChartLabel
    ).toBeVisible();


    // ==================================================
    // CLOSE FULLSCREEN
    // ==================================================

    const backButton =
      page.getByRole(
        "button",
        {
          name:
            /BACK/i,
        }
      );


    await expect(
      backButton
    ).toBeVisible();


    await backButton.click();


    await expect(
      liveChartLabel
    ).not.toBeVisible({
      timeout:
        10_000,
    });


    // ==================================================
    // FINAL CHECKS
    // ==================================================

    expect(
      trackedSymbols.has(
        "ICICIBANK"
      )
    ).toBeTruthy();


    expect(
      scannerCalls.has(
        "ICICIBANK"
      )
    ).toBeTruthy();

  }
);