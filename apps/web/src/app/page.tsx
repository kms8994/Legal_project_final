"use client";

import { FormEvent, useMemo, useState } from "react";

type SearchMode = "statute" | "natural";
type WorkflowStep = "search" | "candidates" | "comparison";

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
  evidence_snippets: EvidenceSnippet[];
  source_url: string | null;
  review_status: string;
  confidence_score: number;
};

type EvidenceSnippet = {
  evidence_id: string;
  section_type: string;
  paragraph_order: number;
  text: string;
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
  pagination: Pagination;
  results: SearchResult[];
};

type Pagination = {
  page: number;
  size: number;
  total: number;
  has_next: boolean;
};

type CaseDetail = {
  case: {
    case_id: string;
    external_id: string;
    case_no: string;
    court_name: string;
    court_level: string | null;
    decision_date: string | null;
    case_name: string;
    case_type: string | null;
    legal_domain: string | null;
    source_url: string | null;
  };
  structure: {
    facts: string | null;
    legal_issue: string | null;
    court_reasoning: string | null;
    conclusion: string | null;
    material_facts: Record<string, unknown>;
    outcome: Record<string, unknown>;
    cited_articles: string[];
    confidence_score: number;
    review_status: string;
  };
};

type CompareCandidates = {
  base_case: {
    case_id: string;
    case_no: string;
    summary_card: string;
    material_facts: Record<string, unknown>;
  };
  candidates: CompareCandidate[];
};

type CompareCandidate = {
  case_id: string;
  case_no: string;
  court_name: string;
  decision_date: string | null;
  case_name: string;
  summary_card: string;
  scores: {
    material_fact_match: number;
    statute_overlap: number;
    facet_match_score: number;
    outcome_difference: number;
    final_score: number;
  };
  common_facts: string[];
  possible_turning_points: string[];
  outcome_difference_summary: string;
  evidence_ids: string[];
};

type CompareAnalysis = {
  base: {
    case_id: string;
    case_no: string;
    court_name: string;
    decision_date: string | null;
    outcome: Record<string, unknown>;
  };
  compare: {
    case_id: string;
    case_no: string;
    court_name: string;
    decision_date: string | null;
    outcome: Record<string, unknown>;
  };
  analysis: {
    common_points: Array<{ text: string }>;
    material_differences: Array<{
      factor: string;
      base: string;
      compare: string;
      meaning: string;
    }>;
    turning_points: Array<{
      title: string;
      explanation: string;
    }>;
    result_difference: string;
  };
};

type ErrorResponse = {
  detail?: {
    message?: string;
  };
};

const DEFAULT_QUERIES: Record<SearchMode, string> = {
  statute: "민법 제750조",
  natural: "교통사고 피해자 과실이 있는 손해배상 사건",
};

const EXAMPLES: Record<SearchMode, string[]> = {
  statute: ["민법 제750조", "민법 제396조", "자동차손배법 제12조의2", "제조물책임법 제3조"],
  natural: [
    "임대차보증금 반환과 건물명도",
    "해고 근로자의 임금과 퇴직금",
    "취득세 부과처분 취소",
    "보험금 청구와 보험자대위",
  ],
};

const MATERIAL_LABELS: Record<string, string> = {
  claim_type: "청구 유형",
  event_type: "사건 유형",
  legal_domain: "법률 분야",
  harm_type: "손해 유형",
  evidence_issue: "증거 쟁점",
  causation_dispute: "인과관계 다툼",
  negligence_dispute: "과실 다툼",
  damage_scope_dispute: "손해 범위 다툼",
  key_disputed_fact: "핵심 다툼",
  outcome_disposition: "판결 결과",
};

export default function Home() {
  const [mode, setMode] = useState<SearchMode>("statute");
  const [query, setQuery] = useState(DEFAULT_QUERIES.statute);
  const [data, setData] = useState<StatuteSearchResponse | NaturalSearchResponse | null>(null);
  const [baseCase, setBaseCase] = useState<SearchResult | null>(null);
  const [baseDetail, setBaseDetail] = useState<CaseDetail | null>(null);
  const [resultDetails, setResultDetails] = useState<Record<string, CaseDetail>>({});
  const [candidates, setCandidates] = useState<CompareCandidate[]>([]);
  const [compareTarget, setCompareTarget] = useState<CompareCandidate | null>(null);
  const [compareDetail, setCompareDetail] = useState<CaseDetail | null>(null);
  const [analysis, setAnalysis] = useState<CompareAnalysis | null>(null);
  const [step, setStep] = useState<WorkflowStep>("search");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSelecting, setIsSelecting] = useState(false);

  const results = useMemo(() => {
    if (!data) return [];
    if (!("query" in data)) return data.results;
    const normalizedRef = data.query.normalized_ref.replace(/\s+/g, "");
    return [...data.results].sort((left, right) => {
      const leftHasArticle = hasArticle(left, normalizedRef);
      const rightHasArticle = hasArticle(right, normalizedRef);
      if (leftHasArticle !== rightHasArticle) return leftHasArticle ? -1 : 1;
      return right.score - left.score;
    });
  }, [data]);

  const resultTitle = useMemo(() => {
    if (!data) return "최근 검색 결과";
    if ("query" in data) return data.query.normalized_ref;
    return data.parsed_intent.legal_issue || data.parsed_intent.facts_summary || "자연어 검색";
  }, [data]);

  function changeMode(nextMode: SearchMode) {
    setMode(nextMode);
    setQuery(DEFAULT_QUERIES[nextMode]);
    resetFlow();
  }

  function resetFlow() {
    setData(null);
    setResultDetails({});
    setBaseCase(null);
    setBaseDetail(null);
    setCandidates([]);
    setCompareTarget(null);
    setCompareDetail(null);
    setAnalysis(null);
    setStep("search");
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setBaseCase(null);
    setBaseDetail(null);
    setResultDetails({});
    setCandidates([]);
    setCompareTarget(null);
    setCompareDetail(null);
    setAnalysis(null);
    setStep("search");

    try {
      const endpoint = mode === "statute" ? "/api/search/statute" : "/api/search/natural";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, page: 1, size: 10, sort: "relevance" }),
      });
      const payload = (await response.json()) as StatuteSearchResponse | NaturalSearchResponse | ErrorResponse;
      if (!response.ok) {
        throw new Error("detail" in payload && payload.detail?.message ? payload.detail.message : "검색에 실패했습니다.");
      }
      const nextData = payload as StatuteSearchResponse | NaturalSearchResponse;
      setData(nextData);
      void hydrateResultDetails(nextData.results);
    } catch (caught) {
      setData(null);
      setError(caught instanceof Error ? caught.message : "검색에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  }

  async function hydrateResultDetails(resultsToHydrate: SearchResult[]) {
    const topResults = resultsToHydrate.slice(0, 10);
    const settled = await Promise.allSettled(
      topResults.map(async (result) => {
        const response = await fetch(`/api/cases/${result.case_id}`);
        if (!response.ok) throw new Error(result.case_id);
        return [result.case_id, (await response.json()) as CaseDetail] as const;
      })
    );
    const nextDetails: Record<string, CaseDetail> = {};
    settled.forEach((item) => {
      if (item.status === "fulfilled") {
        nextDetails[item.value[0]] = item.value[1];
      }
    });
    setResultDetails(nextDetails);
  }

  async function selectBaseCase(result: SearchResult) {
    setIsSelecting(true);
    setError(null);
    setBaseCase(result);
    setCompareTarget(null);
    setCompareDetail(null);
    setAnalysis(null);

    try {
      const [detailResponse, candidatesResponse] = await Promise.all([
        fetch(`/api/cases/${result.case_id}`),
        fetch(`/api/cases/${result.case_id}/compare-candidates?limit=5&require_outcome_difference=true`),
      ]);
      if (!detailResponse.ok) throw new Error("기준 판례 정보를 불러오지 못했습니다.");
      if (!candidatesResponse.ok) throw new Error("유사판례 후보를 불러오지 못했습니다.");
      const detail = (await detailResponse.json()) as CaseDetail;
      const candidatePayload = (await candidatesResponse.json()) as CompareCandidates;
      setBaseDetail(detail);
      setCandidates(candidatePayload.candidates);
      setStep("candidates");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "기준 판례 선택에 실패했습니다.");
    } finally {
      setIsSelecting(false);
    }
  }

  async function selectCompareTarget(candidate: CompareCandidate) {
    if (!baseCase) return;
    setIsSelecting(true);
    setError(null);
    setCompareTarget(candidate);
    setCompareDetail(null);

    try {
      const [response, detailResponse] = await Promise.all([
        fetch("/api/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            base_case_id: baseCase.case_id,
            compare_case_id: candidate.case_id,
          }),
        }),
        fetch(`/api/cases/${candidate.case_id}`),
      ]);
      if (!response.ok) throw new Error("비교 결과를 불러오지 못했습니다.");
      if (!detailResponse.ok) throw new Error("비교 판례 정보를 불러오지 못했습니다.");
      setAnalysis((await response.json()) as CompareAnalysis);
      setCompareDetail((await detailResponse.json()) as CaseDetail);
      setStep("comparison");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "판례 비교에 실패했습니다.");
    } finally {
      setIsSelecting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f5f6f8] text-[#17191d]">
      <header className="border-b border-[#d7dce2] bg-white">
        <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-8">
            <button className="text-xl font-bold text-[#111827]" onClick={resetFlow} type="button">
              CaseLens
            </button>
            <nav className="hidden items-center gap-5 text-sm font-medium text-[#5d6673] md:flex">
              <span className="text-[#111827]">판례검색</span>
              <span>기준판례</span>
              <span>비교</span>
              <span>피드백</span>
            </nav>
          </div>
        </div>
      </header>

      <section className="border-b border-[#d7dce2] bg-white">
        <div className="mx-auto w-full max-w-7xl px-4 py-7 sm:px-6 lg:px-8">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-[#2563eb]">피드백 MVP</p>
              <h1 className="mt-1 text-2xl font-bold text-[#111827] sm:text-3xl">
                검색하고, 기준 판례를 고르고, 한눈에 비교하기
              </h1>
            </div>
            <div className="flex rounded-[6px] border border-[#cfd6df] bg-[#f8fafc] p-1">
              {(["statute", "natural"] as const).map((item) => (
                <button
                  className={`h-10 min-w-24 rounded-[4px] px-4 text-sm font-semibold transition ${
                    mode === item ? "bg-[#111827] text-white shadow-sm" : "text-[#526070] hover:bg-white"
                  }`}
                  key={item}
                  onClick={() => changeMode(item)}
                  type="button"
                >
                  {item === "statute" ? "조문 검색" : "자연어 검색"}
                </button>
              ))}
            </div>
          </div>

          <form className="grid gap-3 lg:grid-cols-[1fr_132px]" onSubmit={handleSubmit}>
            <label className="sr-only" htmlFor="search">검색어</label>
            <input
              className="h-14 w-full rounded-[6px] border border-[#b9c2cf] bg-white px-4 text-base outline-none transition placeholder:text-[#8993a1] focus:border-[#2563eb] focus:ring-3 focus:ring-[#2563eb]/15"
              id="search"
              onChange={(event) => setQuery(event.target.value)}
              placeholder={mode === "statute" ? "예: 민법 제750조" : "예: 교통사고 피해자 과실 손해배상"}
              type="search"
              value={query}
            />
            <button
              className="h-14 rounded-[6px] bg-[#2563eb] px-6 text-base font-bold text-white transition hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:bg-[#9aa8bd]"
              disabled={isLoading || query.trim().length === 0}
              type="submit"
            >
              {isLoading ? "검색 중" : "검색"}
            </button>
          </form>

          <p className="mt-3 text-sm leading-6 text-[#526070]">
            {mode === "statute"
              ? "조문을 입력하면 해당 조문이 인용된 판례를 보여줍니다. 판례를 기준으로 선택하면 같은 화면에서 유사한 사실관계의 판례를 확인할 수 있습니다."
              : "사실관계를 자연어로 입력하면 유사한 사건의 판례를 보여줍니다. 판례를 기준으로 선택하면 같은 화면에서 비교 후보와 비교 결과를 확인할 수 있습니다."}
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            {EXAMPLES[mode].map((example) => (
              <button
                className="rounded-[5px] border border-[#d7dce2] bg-[#f8fafc] px-3 py-1.5 text-sm text-[#465366] transition hover:border-[#2563eb] hover:bg-[#eff6ff] hover:text-[#1d4ed8]"
                key={example}
                onClick={() => setQuery(example)}
                type="button"
              >
                {example}
              </button>
            ))}
          </div>

          <WorkflowPanel step={step} />
        </div>
      </section>

      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {data && "parsed_intent" in data ? (
          <div className="mb-4">
            <ParsedIntentPanel data={data} />
          </div>
        ) : null}

        <section aria-live="polite" className="min-w-0">
          {error ? (
            <div className="mb-4 rounded-[8px] border border-[#f3b1a8] bg-[#fff7f5] p-4 text-sm font-medium text-[#9f3528]">
              {error}
            </div>
          ) : null}

          {step === "comparison" && baseCase && compareTarget ? (
            <ComparisonWorkspace
              analysis={analysis}
              baseCase={baseCase}
              baseDetail={baseDetail}
              compareDetail={compareDetail}
              compareTarget={compareTarget}
              isLoading={isSelecting}
              onBack={() => setStep("candidates")}
            />
          ) : step === "candidates" && baseCase ? (
            <CandidateWorkspace
              baseCase={baseCase}
              baseDetail={baseDetail}
              candidates={candidates}
              isLoading={isSelecting}
              onCompare={selectCompareTarget}
              onBack={() => setStep("search")}
            />
          ) : (
            <SearchWorkspace
              data={data}
              isLoading={isLoading}
              isSelecting={isSelecting}
              resultDetails={resultDetails}
              resultTitle={resultTitle}
              results={results}
              onSelectBase={selectBaseCase}
            />
          )}
        </section>
      </div>
    </main>
  );
}

function SearchWorkspace({
  data,
  isLoading,
  isSelecting,
  resultDetails,
  resultTitle,
  results,
  onSelectBase,
}: {
  data: StatuteSearchResponse | NaturalSearchResponse | null;
  isLoading: boolean;
  isSelecting: boolean;
  resultDetails: Record<string, CaseDetail>;
  resultTitle: string;
  results: SearchResult[];
  onSelectBase: (result: SearchResult) => void;
}) {
  return (
    <>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-[#667085]">{data ? "검색 결과" : "검색 대기"}</p>
          <h2 className="mt-1 text-xl font-bold text-[#111827]">{resultTitle}</h2>
        </div>
        <p className="text-sm font-semibold text-[#465366]">
          {data ? `${data.pagination.total}건` : "예시 검색어를 선택해보세요"}
        </p>
      </div>

      {isLoading ? <LoadingResults /> : null}

      {!isLoading && data ? (
        <div className="grid gap-3">
          {results.map((result, index) => (
            <ResultCard
              detail={resultDetails[result.case_id]}
              index={index + 1}
              isSelecting={isSelecting}
              key={result.case_id}
              onSelect={() => onSelectBase(result)}
              result={result}
            />
          ))}
        </div>
      ) : null}

      {!isLoading && !data ? (
        <div className="rounded-[8px] border border-dashed border-[#b9c2cf] bg-white p-8 text-center">
          <p className="text-base font-bold text-[#111827]">조문이나 사건 사실관계를 입력하세요.</p>
          <p className="mt-2 text-sm text-[#667085]">
            검색 결과에서 기준 판례를 고르면 같은 화면에서 유사판례와 비교 결과가 이어집니다.
          </p>
        </div>
      ) : null}
    </>
  );
}

function CandidateWorkspace({
  baseCase,
  baseDetail,
  candidates,
  isLoading,
  onCompare,
  onBack,
}: {
  baseCase: SearchResult;
  baseDetail: CaseDetail | null;
  candidates: CompareCandidate[];
  isLoading: boolean;
  onCompare: (candidate: CompareCandidate) => void;
  onBack: () => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
      <BaseCasePanel baseCase={baseCase} baseDetail={baseDetail} onBack={onBack} />
      <section className="min-w-0">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm text-[#667085]">유사 사실관계 판례</p>
            <h2 className="mt-1 text-xl font-bold text-[#111827]">비교할 판례를 선택하세요</h2>
          </div>
          <div className="flex items-center gap-3">
            <p className="text-sm font-semibold text-[#465366]">{candidates.length}건</p>
            <button
              className="rounded-[6px] border border-[#94a3b8] bg-white px-4 py-2 text-sm font-bold text-[#1f2937] transition hover:border-[#2563eb] hover:text-[#2563eb]"
              onClick={onBack}
              type="button"
            >
              ← 검색 결과로 돌아가기
            </button>
          </div>
        </div>
        {isLoading ? <LoadingResults /> : null}
        <div className="grid gap-3">
          {candidates.length > 0 ? (
            candidates.map((candidate, index) => (
              <CandidateCard
                candidate={candidate}
                index={index + 1}
                key={candidate.case_id}
                onCompare={() => onCompare(candidate)}
              />
            ))
          ) : (
            <EmptyCard text="유사한 사실관계의 후보 판례를 찾지 못했습니다." />
          )}
        </div>
      </section>
    </div>
  );
}

function ComparisonWorkspace({
  analysis,
  baseCase,
  baseDetail,
  compareDetail,
  compareTarget,
  isLoading,
  onBack,
}: {
  analysis: CompareAnalysis | null;
  baseCase: SearchResult;
  baseDetail: CaseDetail | null;
  compareDetail: CaseDetail | null;
  compareTarget: CompareCandidate;
  isLoading: boolean;
  onBack: () => void;
}) {
  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-[#667085]">판례 비교</p>
          <h2 className="mt-1 text-xl font-bold text-[#111827]">기준 판례와 비교 판례를 한눈에 보기</h2>
        </div>
        <button
          className="rounded-[6px] border border-[#94a3b8] bg-white px-4 py-2 text-sm font-bold text-[#1f2937] transition hover:border-[#2563eb] hover:text-[#2563eb]"
          onClick={onBack}
          type="button"
        >
          ← 비교 후보로 돌아가기
        </button>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <CompareSide title="기준 판례" result={baseCase} detail={baseDetail} />
        <CompareSide title="비교 판례" candidate={compareTarget} detail={compareDetail} />
      </div>

      {isLoading ? <LoadingResults /> : null}

      {analysis ? (
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <AnalysisBlock title="공통점" items={analysis.analysis.common_points.map((item) => item.text)} />
          <AnalysisBlock
            title="주요 차이점"
            items={analysis.analysis.material_differences.map(
              (item) => `${item.factor}: 기준은 ${item.base}, 비교 판례는 ${item.compare}. ${item.meaning}`
            )}
          />
          <AnalysisBlock title="판단을 가른 지점" items={analysis.analysis.turning_points.map((item) => `${item.title}: ${item.explanation}`)} />
          <section className="rounded-[8px] border border-[#d7dce2] bg-white p-4 lg:col-span-3">
            <h3 className="text-sm font-bold text-[#111827]">결론 차이</h3>
            <p className="mt-2 text-sm leading-6 text-[#303846]">{analysis.analysis.result_difference}</p>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function ResultCard({
  detail,
  index,
  isSelecting,
  onSelect,
  result,
}: {
  detail?: CaseDetail;
  index: number;
  isSelecting: boolean;
  onSelect: () => void;
  result: SearchResult;
}) {
  return (
    <article className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <CardHeader
        badge={`관련도 ${Math.round(result.score * 100)}%`}
        courtName={result.court_name}
        date={result.decision_date}
        index={index}
        title={result.case_no || result.case_name}
        subtitle={`${displayCaseName(result.case_name)}${result.legal_domain ? ` · ${result.legal_domain}` : ""}${result.case_type ? ` · ${result.case_type}` : ""}`}
      />
      <SearchNarrativeSections detail={detail} result={result} />
      <Tags items={result.cited_articles.slice(0, 5)} />
      <div className="mt-5 flex flex-wrap gap-2">
        <button
          className="rounded-[5px] bg-[#111827] px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-[#1f2937] disabled:bg-[#9aa8bd]"
          disabled={isSelecting}
          onClick={onSelect}
          type="button"
        >
          {isSelecting ? "불러오는 중" : "기준 판례로 선택"}
        </button>
        <OriginalLink caseNo={result.case_no} sourceUrl={result.source_url} />
      </div>
    </article>
  );
}

function CandidateCard({
  candidate,
  index,
  onCompare,
}: {
  candidate: CompareCandidate;
  index: number;
  onCompare: () => void;
}) {
  return (
    <article className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <CardHeader
        badge={`유사도 ${Math.round(candidate.scores.final_score * 100)}%`}
        courtName={candidate.court_name}
        date={candidate.decision_date}
        index={index}
        title={candidate.case_no}
        subtitle={candidate.case_name}
      />
      <p className="mt-4 text-sm leading-6 text-[#303846]">{candidate.summary_card}</p>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <Score label="사실관계" value={candidate.scores.material_fact_match} />
        <Score label="조문" value={candidate.scores.statute_overlap} />
        <Score label="쟁점" value={candidate.scores.facet_match_score} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="rounded-[5px] bg-[#2563eb] px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-[#1d4ed8]" onClick={onCompare} type="button">
          이 판례와 비교하기
        </button>
        <OriginalLink caseNo={candidate.case_no} />
      </div>
    </article>
  );
}

function BaseCasePanel({
  baseCase,
  baseDetail,
  onBack,
}: {
  baseCase: SearchResult;
  baseDetail: CaseDetail | null;
  onBack: () => void;
}) {
  return (
    <aside className="rounded-[8px] border border-[#d7dce2] bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#2563eb]">기준 판례</p>
          <h2 className="mt-1 text-lg font-bold text-[#111827]">{baseCase.case_no}</h2>
          <p className="mt-1 text-sm text-[#667085]">{displayCaseName(baseCase.case_name)}</p>
        </div>
        <button
          className="rounded-[6px] border border-[#94a3b8] bg-white px-3 py-2 text-sm font-bold text-[#1f2937] transition hover:border-[#2563eb] hover:text-[#2563eb]"
          onClick={onBack}
          type="button"
        >
          ← 검색 결과로 돌아가기
        </button>
      </div>
      <p className="mt-4 text-sm leading-6 text-[#303846]">{baseCase.summary_card}</p>
      <div className="mt-4">
        <OriginalLink caseNo={baseCase.case_no} sourceUrl={baseDetail?.case.source_url ?? baseCase.source_url} />
      </div>
      {baseDetail ? (
        <>
          <InfoSection title="주요 사실" values={baseDetail.structure.material_facts} />
          <InfoSection title="판결 결과" values={baseDetail.structure.outcome} />
          <Tags items={baseDetail.structure.cited_articles} />
        </>
      ) : null}
    </aside>
  );
}

function CompareSide({
  candidate,
  detail,
  result,
  title,
}: {
  candidate?: CompareCandidate;
  detail?: CaseDetail | null;
  result?: SearchResult;
  title: string;
}) {
  const caseNo = result?.case_no ?? candidate?.case_no ?? "-";
  const caseName = result?.case_name ?? candidate?.case_name ?? "-";
  const summary = result?.summary_card ?? candidate?.summary_card ?? "";
  const sourceUrl = detail?.case.source_url ?? result?.source_url ?? null;

  return (
    <article className="rounded-[8px] border border-[#d7dce2] bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#2563eb]">{title}</p>
          <h3 className="mt-1 text-lg font-bold text-[#111827]">{caseNo}</h3>
          <p className="mt-1 text-sm text-[#667085]">{caseName}</p>
        </div>
        <OriginalLink caseNo={caseNo} sourceUrl={sourceUrl} />
      </div>
      <p className="mt-4 text-sm leading-6 text-[#303846]">{summary}</p>
      <CaseNarrativeSections detail={detail} fallbackSummary={summary} />
      {candidate ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <Score label="사실관계" value={candidate.scores.material_fact_match} />
          <Score label="조문" value={candidate.scores.statute_overlap} />
          <Score label="쟁점" value={candidate.scores.facet_match_score} />
        </div>
      ) : null}
    </article>
  );
}

function SearchNarrativeSections({ detail, result }: { detail?: CaseDetail; result: SearchResult }) {
  const facts =
    detail?.structure.facts ||
    summarizeMaterialFacts(detail?.structure.material_facts) ||
    result.summary_card ||
    `${displayCaseName(result.case_name)} 사건입니다.`;
  const reasoning =
    detail?.structure.court_reasoning ||
    detail?.structure.legal_issue ||
    (result.cited_articles.length > 0
      ? `법원은 ${result.cited_articles.slice(0, 3).join(", ")} 등을 중심으로 판단했습니다.`
      : "검색 결과에 구조화된 판단 근거가 아직 없습니다.");
  const judgment = detail?.structure.conclusion || summarizeOutcome(detail?.structure.outcome ?? result.outcome);

  return (
    <div className="mt-5 grid gap-3 lg:grid-cols-3">
      <NarrativeBlock title="사실관계" text={facts} />
      <NarrativeBlock title="법원의 판단 근거" text={reasoning} />
      <NarrativeBlock title="법원의 판결" text={judgment} />
    </div>
  );
}

function CaseNarrativeSections({
  detail,
  fallbackSummary,
}: {
  detail?: CaseDetail | null;
  fallbackSummary: string;
}) {
  const facts = detail?.structure.facts || summarizeMaterialFacts(detail?.structure.material_facts) || fallbackSummary;
  const reasoning =
    detail?.structure.court_reasoning ||
    detail?.structure.legal_issue ||
    "구조화된 법원의 판단 근거가 아직 없습니다. 원문에서 판시사항과 판단 이유를 확인하세요.";
  const judgment = detail?.structure.conclusion || summarizeOutcome(detail?.structure.outcome);

  return (
    <div className="mt-5 grid gap-4">
      <NarrativeBlock title="사실관계" text={facts} />
      <NarrativeBlock title="법원의 판단 근거" text={reasoning} />
      <NarrativeBlock title="법원의 판결" text={judgment} />
    </div>
  );
}

function NarrativeBlock({ title, text }: { title: string; text: string }) {
  return (
    <section className="rounded-[6px] border border-[#e5eaf0] bg-[#fbfcfe] p-4">
      <h4 className="text-sm font-bold text-[#111827]">{title}</h4>
      <p className="mt-2 text-sm leading-6 text-[#303846]">{text}</p>
    </section>
  );
}

function OriginalLink({ caseNo, sourceUrl }: { caseNo: string; sourceUrl?: string | null }) {
  return (
    <a
      className="inline-flex items-center rounded-[5px] border border-[#b9c2cf] bg-white px-3 py-2 text-sm font-semibold text-[#344054] transition hover:border-[#2563eb] hover:text-[#2563eb]"
      href={sourceUrl || lawSearchUrl(caseNo)}
      rel="noreferrer"
      target="_blank"
    >
      원문 보기
    </a>
  );
}

function CardHeader({
  badge,
  courtName,
  date,
  index,
  subtitle,
  title,
}: {
  badge: string;
  courtName: string;
  date: string | null;
  index: number;
  subtitle: string;
  title: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-[#2563eb]">
          {index}. {courtName}
          {date ? ` · ${date}` : ""}
        </p>
        <h3 className="mt-1 text-lg font-bold text-[#111827]">{title}</h3>
        <p className="mt-1 text-sm text-[#667085]">{subtitle}</p>
      </div>
      <div className="rounded-[6px] bg-[#eff6ff] px-3 py-2 text-right text-sm font-bold text-[#1d4ed8]">
        {badge}
      </div>
    </div>
  );
}

function InfoSection({ title, values }: { title: string; values: Record<string, unknown> }) {
  const entries = Object.entries(values).filter(([, value]) => value !== null && value !== "" && value !== "unknown");
  if (entries.length === 0) return null;
  return (
    <section className="mt-4 border-t border-[#e5eaf0] pt-4">
      <h4 className="text-sm font-bold text-[#111827]">{title}</h4>
      <dl className="mt-3 grid gap-2 text-sm">
        {entries.slice(0, 8).map(([key, value]) => (
          <div className="grid grid-cols-[104px_1fr] gap-2" key={key}>
            <dt className="text-[#667085]">{MATERIAL_LABELS[key] ?? key}</dt>
            <dd className="font-medium text-[#303846]">{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[6px] border border-[#e5eaf0] p-3">
      <p className="text-xs font-semibold text-[#667085]">{label}</p>
      <p className="mt-1 text-lg font-bold text-[#111827]">{Math.round(value * 100)}%</p>
    </div>
  );
}

function AnalysisBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-4">
      <h3 className="text-sm font-bold text-[#111827]">{title}</h3>
      {items.length > 0 ? (
        <ul className="mt-3 grid gap-2 text-sm leading-6 text-[#303846]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-[#667085]">구조화된 내용이 없습니다.</p>
      )}
    </section>
  );
}

function Tags({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {items.slice(0, 8).map((item) => (
        <span className="rounded-[5px] border border-[#d7dce2] px-2.5 py-1 text-xs text-[#4b5563]" key={item}>
          {item}
        </span>
      ))}
    </div>
  );
}

function WorkflowPanel({ step }: { step: WorkflowStep }) {
  const items = [
    ["search", "검색"],
    ["candidates", "기준 판례"],
    ["comparison", "비교"],
  ] as const;
  return (
    <section className="mt-5 rounded-[8px] border border-[#d7dce2] bg-[#f8fafc] px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-bold text-[#111827]">사용자 흐름</h2>
        <ol className="flex flex-1 flex-wrap items-center gap-2 text-sm">
        {items.map(([key, label], index) => (
          <li
            className={`flex min-w-32 items-center gap-2 rounded-[6px] px-3 py-2 ${
              step === key ? "bg-[#eff6ff] font-bold text-[#2563eb]" : "text-[#667085]"
            }`}
            key={key}
          >
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                step === key ? "bg-[#2563eb] text-white" : "bg-[#eef2f7] text-[#667085]"
              }`}
            >
              {index + 1}
            </span>
            {label}
          </li>
        ))}
        </ol>
      </div>
    </section>
  );
}

function ParsedIntentPanel({ data }: { data: NaturalSearchResponse }) {
  const intent = data.parsed_intent;
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-sm font-bold text-[#111827]">쟁점 분석</h2>
        <span className="rounded-[5px] bg-[#eef2f7] px-2 py-1 text-xs font-bold text-[#465366]">
          {Math.round(intent.confidence * 100)}%
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[#374151]">{intent.facts_summary}</p>
      <Tags items={[...intent.keywords.slice(0, 8), ...intent.inferred_articles]} />
    </section>
  );
}

function LoadingResults() {
  return (
    <div className="grid gap-3">
      {[0, 1, 2].map((item) => (
        <div className="rounded-[8px] border border-[#d7dce2] bg-white p-5" key={item}>
          <div className="h-4 w-40 animate-pulse rounded bg-[#e5eaf0]" />
          <div className="mt-3 h-6 w-2/3 animate-pulse rounded bg-[#e5eaf0]" />
          <div className="mt-4 h-16 w-full animate-pulse rounded bg-[#eef2f7]" />
        </div>
      ))}
    </div>
  );
}

function EmptyCard({ text }: { text: string }) {
  return <div className="rounded-[8px] border border-dashed border-[#b9c2cf] bg-white p-6 text-sm text-[#667085]">{text}</div>;
}

function displayCaseName(caseName: string) {
  return caseName.trim().length > 0 ? caseName.trim() : "사건명 없음";
}

function formatValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "있음" : "없음";
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function summarizeMaterialFacts(values?: Record<string, unknown>): string {
  if (!values) return "";
  const entries = Object.entries(values)
    .filter(([, value]) => value !== null && value !== "" && value !== "unknown")
    .slice(0, 6);
  if (entries.length === 0) return "";
  return entries
    .map(([key, value]) => `${MATERIAL_LABELS[key] ?? key}: ${formatValue(value)}`)
    .join(", ");
}

function summarizeOutcome(values?: Record<string, unknown>): string {
  if (!values) return "구조화된 판결 결과가 아직 없습니다. 원문에서 주문과 결론을 확인하세요.";
  const summary = summarizeMaterialFacts(values);
  return summary || "구조화된 판결 결과가 아직 없습니다. 원문에서 주문과 결론을 확인하세요.";
}

function lawSearchUrl(caseNo: string) {
  return `https://www.law.go.kr/LSW/precSc.do?menuId=7&subMenuId=47&tabMenuId=213&query=${encodeURIComponent(caseNo)}`;
}

function hasArticle(result: SearchResult, normalizedRef: string) {
  return result.cited_articles.some((article) => article.replace(/\s+/g, "") === normalizedRef);
}
