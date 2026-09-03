import {
  NextResponse,
} from "next/server";

import {
  readFile,
} from "fs/promises";

import path from "path";

export const dynamic =
  "force-dynamic";

export async function GET() {
  try {
    const file =
      path.resolve(
        process.cwd(),
        "../backend/logs/full_market_scanner.json",
      );

    const raw =
      await readFile(
        file,
        "utf8",
      );

    const data =
      JSON.parse(
        raw,
      );

    return NextResponse.json(
      data,
      {
        headers: {
          "Cache-Control":
            "no-store, max-age=0",
        },
      },
    );

  } catch (error) {
    return NextResponse.json({
      status:
        "STARTING",

      total_nse_equities:
        0,

      quoted_count:
        0,

      waiting_count:
        0,

      all_stocks:
        [],

      rising:
        [],

      falling:
        [],

      gainers:
        [],

      losers:
        [],

      volume_activity:
        [],

      error:
        error instanceof Error
          ? error.message
          : "Scanner snapshot not ready",
    });
  }
}
