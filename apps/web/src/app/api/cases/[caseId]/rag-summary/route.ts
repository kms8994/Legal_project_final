import { NextResponse } from "next/server";

const SEARCH_API_URL = process.env.SEARCH_API_URL ?? "http://localhost:8000";

type RouteContext = {
  params: Promise<{
    caseId: string;
  }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const { caseId } = await context.params;

  try {
    const response = await fetch(`${SEARCH_API_URL}/api/v1/cases/${caseId}/rag-summary`, {
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
          message: "판례 요약 API에 연결할 수 없습니다.",
        },
      },
      { status: 503 }
    );
  }
}
