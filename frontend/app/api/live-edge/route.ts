import {
  NextRequest,
  NextResponse,
} from "next/server";


const BACKEND =
  "http://localhost:8000";


export async function GET(
  request: NextRequest,
) {
  try {
    const cookie =
      request.headers.get("cookie") || "";

    const response = await fetch(
      `${BACKEND}/api/v2/fast-scan`,
      {
        method: "GET",

        cache: "no-store",

        headers: {
          cookie,
          accept: "application/json",
        },
      },
    );

    const text =
      await response.text();

    let body: unknown;

    try {
      body = JSON.parse(text);
    } catch {
      body = {
        detail: text,
      };
    }

    return NextResponse.json(
      body,
      {
        status: response.status,
      },
    );

  } catch (error) {

    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? error.message
            : "Live Edge proxy failed",
      },
      {
        status: 500,
      },
    );
  }
}
