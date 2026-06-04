"use client";

import { FormEvent, useState } from "react";

type SearchResult = {
  case_id: string;
  case_no: string;
  court_name: string;
  court_level: string | null;
  decision_date: string | null;
  case_name: string;
  case_type: string | null;
  legal_domain: string | null;
  summary_card: string;
  outcome: Record<string, unknown>;
  cited_articles: string[];
  score: number;
  evidence_ids: string[];
  source_url: string | null;
  review_status: string;
  confidence_score: number;
};

type SearchResponse = {
  query: {
    raw: string;
    normalized_ref: string;
    law_name: string;
    article_no: string;
    article_validated: boolean;
  };
  pagination: {
    page: number;
    size: number;
    total: number;
    has_next: boolean;
  };
  results: SearchResult[];
};

type ErrorResponse = {
  detail?: {
    code?: string;
    message?: string;
  };
};

const DEFAULT_QUERY = "민법 제750조";

export default function Home() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/search/statute", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          page: 1,
          size: 10,
          sort: "relevance",
        }),
      });

      const payload = (await response.json()) as SearchResponse | ErrorResponse;

      if (!response.ok) {
        const message =
          "detail" in payload && payload.detail?.message
            ? payload.detail.message
            : "검색 중 오류가 발생했습니다.";
        throw new Error(message);
      }

      setData(payload as SearchResponse);
    } catch (caught) {
      setData(null);
      setError(caught instanceof Error ? caught.message : "검색 중 오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#191a17]">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-6 sm:px-8 lg:px-10">
        <header className="flex items-center justify-between border-b border-[#d8d8cf] pb-4">
          <div>
            <p className="font-mono text-xs uppercase text-[#6d7165]">CaseLens</p>
            <h1 className="mt-1 text-2xl font-semibold">손해배상 판례 검색</h1>
          </div>
          <span className="hidden rounded border border-[#c7c8bd] px-3 py-1 text-sm text-[#5b5f55] sm:inline">
            Supabase DB 연결됨
          </span>
        </header>

        <div className="grid flex-1 content-start gap-8 py-10 lg:grid-cols-[minmax(0,0.82fr)_minmax(360px,1.18fr)]">
          <section>
            <div className="mb-5 flex w-full max-w-xl rounded border border-[#c7c8bd] bg-white p-1">
              {["조문", "자연어", "사건번호"].map((mode, index) => (
                <button
                  key={mode}
                  className={`h-10 flex-1 text-sm font-medium transition ${
                    index === 0
                      ? "bg-[#1f3d36] text-white"
                      : "text-[#51564e] hover:bg-[#eeeeea]"
                  }`}
                  type="button"
                  disabled={index !== 0}
                >
                  {mode}
                </button>
              ))}
            </div>

            <form className="grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={handleSubmit}>
              <label className="sr-only" htmlFor="search">
                판례 검색어
              </label>
              <input
                id="search"
                className="h-14 w-full border border-[#bbbdb1] bg-white px-4 text-base outline-none transition focus:border-[#1f3d36] focus:ring-2 focus:ring-[#1f3d36]/20"
                placeholder="민법 제750조"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <button
                className="h-14 bg-[#1f3d36] px-8 text-base font-semibold text-white transition hover:bg-[#17312b] disabled:cursor-not-allowed disabled:bg-[#87918b]"
                type="submit"
                disabled={isLoading || query.trim().length === 0}
              >
                {isLoading ? "검색 중" : "검색"}
              </button>
            </form>

            <div className="mt-8 grid gap-3 text-sm text-[#555950] sm:grid-cols-3 lg:grid-cols-1">
              <div className="border-l-2 border-[#aab2a0] pl-3">
                조문을 정규화하고 내부 DB에서 검증합니다.
              </div>
              <div className="border-l-2 border-[#aab2a0] pl-3">
                인용 조문이 연결된 판례를 신뢰도순으로 정렬합니다.
              </div>
              <div className="border-l-2 border-[#aab2a0] pl-3">
                판례 요약, 결론, 근거 문단 ID를 함께 확인합니다.
              </div>
            </div>
          </section>

          <section aria-live="polite">
            {error ? (
              <div className="border border-[#b96b5c] bg-[#fff6f3] p-4 text-sm text-[#7e2f22]">
                {error}
              </div>
            ) : null}

            {data ? (
              <div>
                <div className="mb-4 flex flex-wrap items-end justify-between gap-3 border-b border-[#d8d8cf] pb-3">
                  <div>
                    <p className="text-sm text-[#666b61]">정규화된 조문</p>
                    <h2 className="text-xl font-semibold">{data.query.normalized_ref}</h2>
                  </div>
                  <p className="text-sm text-[#555950]">총 {data.pagination.total}건</p>
                </div>

                <div className="grid gap-3">
                  {data.results.map((result) => (
                    <article
                      className="rounded border border-[#d3d4ca] bg-white p-4 shadow-sm"
                      key={result.case_id}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-[#44615a]">
                            {result.court_name}
                            {result.decision_date ? ` · ${result.decision_date}` : ""}
                          </p>
                          <h3 className="mt-1 text-lg font-semibold">{result.case_name}</h3>
                          <p className="mt-1 text-sm text-[#666b61]">{result.case_no}</p>
                        </div>
                        <span className="rounded bg-[#eef0e8] px-2 py-1 text-sm text-[#4d534a]">
                          신뢰도 {Math.round(result.confidence_score * 100)}%
                        </span>
                      </div>

                      <p className="mt-3 text-sm leading-6 text-[#30332d]">
                        {result.summary_card}
                      </p>

                      <div className="mt-4 flex flex-wrap gap-2 text-xs text-[#555950]">
                        {result.cited_articles.map((article) => (
                          <span className="rounded border border-[#d3d4ca] px-2 py-1" key={article}>
                            {article}
                          </span>
                        ))}
                        {result.evidence_ids.map((id) => (
                          <span className="rounded bg-[#f2eadf] px-2 py-1" key={id}>
                            근거 {id}
                          </span>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <div className="border border-[#d3d4ca] bg-white p-5 text-sm leading-6 text-[#555950]">
                기본 검색어로 <span className="font-semibold text-[#191a17]">민법 제750조</span>를
                입력해두었습니다. 검색하면 Supabase에 적재한 샘플 판례 3건을 확인할 수 있습니다.
              </div>
            )}
          </section>
        </div>

        <footer className="border-t border-[#d8d8cf] pt-4 text-sm text-[#666b61]">
          검색 결과와 AI 요약은 참고용입니다. 실제 판단은 판례 원문, 최신 법령, 전문가 검토로
          확인해야 합니다.
        </footer>
      </section>
    </main>
  );
}
