"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

type SearchMode = "statute" | "natural";

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
  evidence_snippets: {
    evidence_id: string;
    section_type: string;
    paragraph_order: number;
    text: string;
  }[];
  source_url: string | null;
  review_status: string;
  confidence_score: number;
};

type StatuteSearchResponse = {
  query: {
    raw: string;
    normalized_ref: string;
    law_name: string;
    article_no: string;
    article_validated: boolean;
  };
  pagination: Pagination;
  results: SearchResult[];
};

type NaturalSearchResponse = {
  parsed_intent: {
    case_type: string | null;
    legal_domain: string | null;
    keywords: string[];
    legal_issue: string | null;
    inferred_articles: string[];
    facts_summary: string;
    confidence: number;
    needs_clarification: boolean;
    clarification_question: string | null;
  };
  search_method: "structured_fallback";
  pagination: Pagination;
  results: SearchResult[];
};

type Pagination = {
  page: number;
  size: number;
  total: number;
  has_next: boolean;
};

type SearchResponse = StatuteSearchResponse | NaturalSearchResponse;

type ErrorResponse = {
  detail?: {
    code?: string;
    message?: string;
  };
};

const DEFAULT_QUERIES: Record<SearchMode, string> = {
  statute: "민법 제750조",
  natural: "traffic accident victim negligence damages",
};

export default function Home() {
  const [mode, setMode] = useState<SearchMode>("statute");
  const [query, setQuery] = useState(DEFAULT_QUERIES.statute);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  function changeMode(nextMode: SearchMode) {
    setMode(nextMode);
    setQuery(DEFAULT_QUERIES[nextMode]);
    setData(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const endpoint = mode === "statute" ? "/api/search/statute" : "/api/search/natural";
      const response = await fetch(endpoint, {
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
            : "Search failed.";
        throw new Error(message);
      }

      setData(payload as SearchResponse);
    } catch (caught) {
      setData(null);
      setError(caught instanceof Error ? caught.message : "Search failed.");
    } finally {
      setIsLoading(false);
    }
  }

  const results = data?.results ?? [];

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#191a17]">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-6 sm:px-8 lg:px-10">
        <header className="flex items-center justify-between border-b border-[#d8d8cf] pb-4">
          <div>
            <p className="font-mono text-xs uppercase text-[#6d7165]">CaseLens</p>
            <h1 className="mt-1 text-2xl font-semibold">Damages precedent search</h1>
          </div>
          <span className="hidden border border-[#c7c8bd] px-3 py-1 text-sm text-[#5b5f55] sm:inline">
            Structured fallback MVP
          </span>
        </header>

        <div className="grid flex-1 content-start gap-8 py-10 lg:grid-cols-[minmax(0,0.82fr)_minmax(360px,1.18fr)]">
          <section>
            <div className="mb-5 flex w-full max-w-xl border border-[#c7c8bd] bg-white p-1">
              {(["statute", "natural"] as const).map((item) => (
                <button
                  className={`h-10 flex-1 text-sm font-medium transition ${
                    mode === item
                      ? "bg-[#1f3d36] text-white"
                      : "text-[#51564e] hover:bg-[#eeeeea]"
                  }`}
                  key={item}
                  onClick={() => changeMode(item)}
                  type="button"
                >
                  {item === "statute" ? "Statute" : "Natural"}
                </button>
              ))}
            </div>

            <form className="grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={handleSubmit}>
              <label className="sr-only" htmlFor="search">
                Search query
              </label>
              <input
                className="h-14 w-full border border-[#bbbdb1] bg-white px-4 text-base outline-none transition focus:border-[#1f3d36] focus:ring-2 focus:ring-[#1f3d36]/20"
                id="search"
                onChange={(event) => setQuery(event.target.value)}
                placeholder={mode === "statute" ? "민법 제750조" : "traffic accident victim negligence"}
                type="search"
                value={query}
              />
              <button
                className="h-14 bg-[#1f3d36] px-8 text-base font-semibold text-white transition hover:bg-[#17312b] disabled:cursor-not-allowed disabled:bg-[#87918b]"
                disabled={isLoading || query.trim().length === 0}
                type="submit"
              >
                {isLoading ? "Searching..." : "Search"}
              </button>
            </form>

            <div className="mt-8 grid gap-3 text-sm text-[#555950] sm:grid-cols-3 lg:grid-cols-1">
              <div className="border-l-2 border-[#aab2a0] pl-3">
                Statute mode validates an article against the internal DB.
              </div>
              <div className="border-l-2 border-[#aab2a0] pl-3">
                Natural mode parses intent and ranks structured case data.
              </div>
              <div className="border-l-2 border-[#aab2a0] pl-3">
                Result cards link into detail, candidates, comparison, and feedback.
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
                    <p className="text-sm text-[#666b61]">
                      {mode === "statute" ? "Validated statute" : "Parsed intent"}
                    </p>
                    <h2 className="text-xl font-semibold">
                      {"query" in data ? data.query.normalized_ref : data.parsed_intent.legal_issue}
                    </h2>
                  </div>
                  <p className="text-sm text-[#555950]">{data.pagination.total} results</p>
                </div>

                {"parsed_intent" in data ? <ParsedIntentPanel data={data} /> : null}

                <div className="grid gap-3">
                  {results.map((result) => (
                    <article
                      className="border border-[#d3d4ca] bg-white p-4 shadow-sm"
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
                        <span className="bg-[#eef0e8] px-2 py-1 text-sm text-[#4d534a]">
                          Score {Math.round(result.score * 100)}%
                        </span>
                      </div>

                      <p className="mt-3 text-sm leading-6 text-[#30332d]">
                        {result.summary_card}
                      </p>

                      {result.evidence_snippets.length > 0 ? (
                        <div className="mt-4 border-l-2 border-[#c7b89d] bg-[#fbfaf6] px-3 py-2">
                          <p className="text-xs font-semibold uppercase text-[#6d6251]">
                            Evidence
                          </p>
                          <div className="mt-2 grid gap-2">
                            {result.evidence_snippets.slice(0, 2).map((snippet) => (
                              <p
                                className="text-sm leading-6 text-[#3c3f38]"
                                key={`${snippet.evidence_id}-${snippet.paragraph_order}`}
                              >
                                <span className="font-semibold text-[#6b5b3f]">
                                  {snippet.evidence_id}
                                </span>{" "}
                                {snippet.text}
                              </p>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      <div className="mt-4 flex flex-wrap gap-3">
                        <Link
                          className="text-sm font-semibold text-[#1f3d36] hover:underline"
                          href={`/cases/${result.case_id}`}
                        >
                          View detail
                        </Link>
                        <Link
                          className="text-sm font-semibold text-[#1f3d36] hover:underline"
                          href={`/cases/${result.case_id}/compare`}
                        >
                          Compare candidates
                        </Link>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2 text-xs text-[#555950]">
                        {result.cited_articles.map((article) => (
                          <span className="border border-[#d3d4ca] px-2 py-1" key={article}>
                            {article}
                          </span>
                        ))}
                        {result.evidence_ids.map((id) => (
                          <span className="bg-[#f2eadf] px-2 py-1" key={id}>
                            Evidence {id}
                          </span>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <div className="border border-[#d3d4ca] bg-white p-5 text-sm leading-6 text-[#555950]">
                Start with a statute query or switch to natural search.
              </div>
            )}
          </section>
        </div>

        <footer className="border-t border-[#d8d8cf] pt-4 text-sm text-[#666b61]">
          CaseLens outputs are reference material. Review official source text before relying on
          any legal conclusion.
        </footer>
      </section>
    </main>
  );
}

function ParsedIntentPanel({ data }: { data: NaturalSearchResponse }) {
  const intent = data.parsed_intent;
  return (
    <section className="mb-4 border border-[#d3d4ca] bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase text-[#5b5f55]">Intent</p>
          <p className="mt-1 text-sm text-[#30332d]">{intent.facts_summary}</p>
        </div>
        <span className="bg-[#eef0e8] px-2 py-1 text-sm text-[#4d534a]">
          {Math.round(intent.confidence * 100)}%
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-[#555950]">
        {intent.keywords.map((keyword) => (
          <span className="border border-[#d3d4ca] px-2 py-1" key={keyword}>
            {keyword}
          </span>
        ))}
        {intent.inferred_articles.map((article) => (
          <span className="bg-[#f2eadf] px-2 py-1" key={article}>
            {article}
          </span>
        ))}
      </div>
      {intent.needs_clarification && intent.clarification_question ? (
        <p className="mt-3 text-sm text-[#7e2f22]">{intent.clarification_question}</p>
      ) : null}
    </section>
  );
}
