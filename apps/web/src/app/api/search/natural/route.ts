import { NextResponse } from "next/server";

const SEARCH_API_URL = process.env.SEARCH_API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const body = await request.json();
  try {
    const response = await fetch(`${SEARCH_API_URL}/api/v1/search/natural`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
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
          message: "자연어 검색 API에 연결할 수 없습니다.",
        },
      },
      { status: 503 }
    );
  }
}
