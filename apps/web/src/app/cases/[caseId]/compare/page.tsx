import Link from "next/link";
import { notFound } from "next/navigation";

const SEARCH_API_URL = process.env.SEARCH_API_URL ?? "http://localhost:8000";

type CompareCandidates = {
  base_case: {
    case_id: string;
    case_no: string;
    summary_card: string;
    material_facts: Record<string, unknown>;
  };
  ranking_policy: {
    policy_name: string;
    outcome_difference_weight: number;
  };
  candidates: Array<{
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
  }>;
  relaxation_attempts: Array<{
    level: number;
    description: string;
    result_count: number;
  }>;
};

type ComparePageProps = {
  params: Promise<{
    caseId: string;
  }>;
};

async function getCompareCandidates(caseId: string): Promise<CompareCandidates> {
  const response = await fetch(
    `${SEARCH_API_URL}/api/v1/cases/${caseId}/compare-candidates?limit=5&require_outcome_difference=true`,
    {
      cache: "no-store",
    }
  );

  if (response.status === 404) {
    notFound();
  }

  if (!response.ok) {
    throw new Error("유사판례 후보 요청에 실패했습니다.");
  }

  return response.json() as Promise<CompareCandidates>;
}

export default async function CompareCandidatesPage({ params }: ComparePageProps) {
  const { caseId } = await params;
  const data = await getCompareCandidates(caseId);

  return (
    <main className="min-h-screen bg-[#f5f6f8] text-[#17191d]">
      <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="border-b border-[#d7dce2] pb-5">
          <div className="flex flex-wrap gap-3 text-sm font-semibold text-[#2563eb]">
            <Link className="hover:underline" href="/">
              검색
            </Link>
            <Link className="hover:underline" href={`/cases/${caseId}`}>
              기준 판례
            </Link>
          </div>
          <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-[#2563eb]">유사판례 후보</p>
              <h1 className="mt-1 text-2xl font-bold text-[#111827]">{data.base_case.case_no}</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[#526070]">
                {data.base_case.summary_card || "기준 판례 요약이 없습니다."}
              </p>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-[#526070]">
                기준 판례와 사실관계가 유사한 후보입니다. 비교하고 싶은 판례를 선택하면
                두 판례의 공통점, 차이점, 결론 차이를 확인할 수 있습니다.
              </p>
            </div>
            <div className="rounded-[6px] border border-[#d7dce2] bg-[#f8fafc] px-3 py-2 text-sm font-semibold text-[#465366]">
              유사도 우선 정렬
            </div>
          </div>
        </header>

        <section className="grid gap-3">
          {data.candidates.length > 0 ? (
            data.candidates.map((candidate, index) => (
              <article className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm" key={candidate.case_id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[#2563eb]">
                      후보 판례 {index + 1}
                    </p>
                    <h2 className="mt-1 text-lg font-bold text-[#111827]">{candidate.case_name}</h2>
                    <p className="mt-1 text-sm text-[#667085]">
                      {candidate.case_no} · {candidate.court_name}
                      {candidate.decision_date ? ` · ${candidate.decision_date}` : ""}
                    </p>
                  </div>
                  <div className="rounded-[6px] bg-[#eff6ff] px-3 py-2 text-sm font-bold text-[#1d4ed8]">
                    종합 유사도 {index + 1}순위
                  </div>
                </div>

                <p className="mt-3 text-sm leading-6 text-[#303846]">{candidate.summary_card}</p>

                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <Score label="사실관계 유사도" value={candidate.scores.material_fact_match} />
                  <Score label="조문 중복도" value={candidate.scores.statute_overlap} />
                  <Score label="쟁점 유사도" value={candidate.scores.facet_match_score} />
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <ListBlock items={candidate.common_facts} title="공통 사실관계" />
                  <ListBlock items={candidate.possible_turning_points} title="차이가 날 수 있는 지점" />
                </div>

                <div className="mt-4 border-t border-[#e5eaf0] pt-3">
                  <p className="text-sm font-bold text-[#111827]">결론 차이 요약</p>
                  <p className="mt-1 text-sm leading-6 text-[#303846]">
                    {candidate.outcome_difference_summary}
                  </p>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {candidate.evidence_ids.map((id) => (
                    <span className="rounded-[5px] border border-[#d7dce2] px-2 py-1 text-xs text-[#465366]" key={id}>
                      근거 {id}
                    </span>
                  ))}
                  <Link
                    className="rounded-[5px] bg-[#2563eb] px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-[#1d4ed8]"
                    href={`/compare?base=${caseId}&target=${candidate.case_id}`}
                  >
                    이 판례와 비교하기
                  </Link>
                  <Link
                    className="ml-auto rounded-[5px] border border-[#b9c2cf] bg-white px-3 py-2 text-sm font-semibold text-[#344054] transition hover:border-[#2563eb] hover:text-[#2563eb]"
                    href={`/cases/${candidate.case_id}`}
                  >
                    판례 상세 보기
                  </Link>
                </div>
              </article>
            ))
          ) : (
            <div className="rounded-[8px] border border-dashed border-[#b9c2cf] bg-white p-5 text-sm text-[#667085]">
              비교할 유사판례 후보를 찾지 못했습니다.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function scoreLevel(value: number): string {
  if (value < 0.15) return "낮음";
  if (value < 0.45) return "보통";
  return "높음";
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[6px] border border-[#e5eaf0] p-3">
      <p className="text-xs font-semibold text-[#667085]">{label}</p>
      <p className="mt-1 text-lg font-bold text-[#111827]">{scoreLevel(value)}</p>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-[6px] border border-[#e5eaf0] bg-[#fbfcfe] p-3">
      <h3 className="text-sm font-bold text-[#111827]">{title}</h3>
      {items.length > 0 ? (
        <ul className="mt-2 grid gap-1 text-sm text-[#303846]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[#667085]">구조화된 신호가 없습니다.</p>
      )}
    </section>
  );
}
