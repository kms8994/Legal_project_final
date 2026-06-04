import { NextResponse } from "next/server";

const SEARCH_API_URL = process.env.SEARCH_API_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const body = await request.json();

  try {
    const response = await fetch(`${SEARCH_API_URL}/api/v1/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const payload = await response.json();

    return NextResponse.json(payload, {
      status: response.status,
    });
  } catch {
    return NextResponse.json(
      {
        detail: {
          code: "SEARCH_API_UNAVAILABLE",
          message: "Feedback API is unavailable.",
        },
      },
      { status: 503 }
    );
  }
}
