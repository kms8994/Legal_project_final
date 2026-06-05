import { NextResponse } from "next/server";

const SEARCH_API_URL = process.env.SEARCH_API_URL ?? "http://localhost:8000";

type RouteContext = {
  params: Promise<{
    caseId: string;
  }>;
};

export async function GET(request: Request, context: RouteContext) {
  const { caseId } = await context.params;
  const { searchParams } = new URL(request.url);
  const query = searchParams.toString();
  const path = `/api/v1/cases/${caseId}/compare-candidates${query ? `?${query}` : ""}`;

  try {
    const response = await fetch(`${SEARCH_API_URL}${path}`, {
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
          message: "유사판례 후보 API에 연결할 수 없습니다.",
        },
      },
      { status: 503 }
    );
  }
}
