import {
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import userEvent from
  "@testing-library/user-event";

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import MarketRadarPanel from
  "../components/dashboard/MarketRadarPanel";


describe(
  "MarketRadarPanel",
  () => {

    beforeEach(
      () => {

        const fetchMock =
          vi.fn(
            async (
              input:
                RequestInfo |
                URL
            ) => {

              const url =
                String(input);


              if (
                url.includes(
                  "/api/watchlist/symbols"
                )
              ) {

                return new Response(
                  JSON.stringify(
                    []
                  ),
                  {
                    status:
                      200,

                    headers: {
                      "Content-Type":
                        "application/json",
                    },
                  }
                );

              }


              if (
                url.includes(
                  "/api/instruments?"
                )
              ) {

                return new Response(
                  JSON.stringify(
                    {
                      items: [
                        {
                          exchange:
                            "NSE",

                          symbol:
                            "ICICIBANK",

                          name:
                            "ICICI Bank Ltd",

                          token:
                            "4963",

                          kind:
                            "EQUITY",
                        },
                      ],

                      page:
                        1,

                      page_size:
                        50,

                      total:
                        1,

                      pages:
                        1,
                    }
                  ),
                  {
                    status:
                      200,

                    headers: {
                      "Content-Type":
                        "application/json",
                    },
                  }
                );

              }


              throw new Error(
                `Unexpected request: ${url}`
              );

            }
          );


        vi.stubGlobal(
          "fetch",
          fetchMock
        );

      }
    );


    afterEach(
      () => {

        vi.unstubAllGlobals();

        vi.restoreAllMocks();

      }
    );


    it(
      "adds an NSE Universe stock to the watchlist",
      async () => {

        const user =
          userEvent.setup();


        const onAdd =
          vi.fn()
            .mockResolvedValue(
              undefined
            );


        const openStock =
          vi.fn();


        render(
          <MarketRadarPanel
            apiBase="http://localhost:8000"
            liveStocks={[]}
            scanners={{}}
            onOpenStock={
              openStock
            }
            onAddToWatchlist={
              onAdd
            }
          />
        );


        await user.click(
          screen.getByRole(
            "button",
            {
              name:
                "NSE UNIVERSE",
            }
          )
        );


        expect(
          await screen.findByText(
            "ICICIBANK"
          )
        ).toBeInTheDocument();


        const addButton =
          await screen.findByRole(
            "button",
            {
              name:
                "+ WATCH",
            }
          );


        await user.click(
          addButton
        );


        await waitFor(
          () => {

            expect(
              onAdd
            ).toHaveBeenCalledTimes(
              1
            );

          }
        );


        expect(
          onAdd
        ).toHaveBeenCalledWith(
          expect.objectContaining(
            {
              symbol:
                "ICICIBANK",

              token:
                "4963",
            }
          )
        );


        await waitFor(
          () => {

            expect(
              screen
                .getAllByText(
                  /TRACKED/
                )
                .length
            ).toBeGreaterThan(
              0
            );

          }
        );

      }
    );

  }
);
