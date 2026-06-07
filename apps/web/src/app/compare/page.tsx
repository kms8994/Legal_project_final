import Link from "next/link";
import { notFound } from "next/navigation";
import { FeedbackForm } from "./FeedbackForm";

const SEARCH_API_URL = process.env.SEARCH_API_URL ?? "http://localhost:8000";

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
    common_points: Array<{
      text: string;
      evidence_ids: {
        base: string[];
        compare: string[];
      };
    }>;
    material_differences: Array<{
      factor: string;
      base: string;
      compare: string;
      meaning: string;
      evidence_ids: {
        base: string[];
        compare: string[];
      };
    }>;
    turning_points: Array<{
      title: string;
      explanation: string;
      evidence_ids: {
        base: string[];
        compare: string[];
      };
    }>;
    result_difference: string;
    generated_by: string;
    fallback_used: boolean;
    fallback_reason: string | null;
  };
  evidence_links: {
    base: Array<{
      evidence_id: string;
      section_type: string;
      text: string;
    }>;
    compare: Array<{
      evidence_id: string;
      section_type: string;
      text: string;
    }>;
  };
  disclaimer: string;
};

type ComparePageProps = {
  searchParams: Promise<{
    base?: string;
    target?: string;
  }>;
};

async function getAnalysis(baseCaseId: string, compareCaseId: string): Promise<CompareAnalysis> {
  const response = await fetch(`${SEARCH_API_URL}/api/v1/compare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      base_case_id: baseCaseId,
      compare_case_id: compareCaseId,
    }),
    cache: "no-store",
  });

  if (response.status === 404) {
    notFound();
  }

  if (!response.ok) {
    throw new Error("판례 비교 분석 요청에 실패했습니다.");
  }

  return response.json() as Promise<CompareAnalysis>;
}

const OUTCOME_KEY_LABELS: Record<string, string> = {
  direction: "판결 방향",
  disposition: "주문",
  key_factor: "주요 판단 요소",
  ratio_or_percentage: "비율",
  confidence: "신뢰도",
  outcome_disposition: "판결 결과",
};

const OUTCOME_VALUE_LABELS: Record<string, string> = {
  "true": "있음",
  "false": "없음",
  "True": "있음",
  "False": "없음",
  damages: "손해배상",
  injury: "신체 침해",
  property: "재산 피해",
  wrongful_death: "사망",
  plaintiff_wins: "원고 승",
  defendant_wins: "피고 승",
  partial: "일부 인용",
  dismissed: "기각",
  unknown: "미확인",
};

function formatOutcome(outcome: Record<string, unknown>): string {
  const entries = Object.entries(outcome).filter(([, v]) => v !== null && v !== "" && v !== undefined);
  if (entries.length === 0) {
    return "구조화된 결과가 없습니다.";
  }
  return entries
    .map(([key, value]) => {
      const label = OUTCOME_KEY_LABELS[key] ?? key;
      const raw = String(value);
      const valLabel = OUTCOME_VALUE_LABELS[raw] ?? raw;
      return `${label}: ${valLabel}`;
    })
    .join(" · ");
}

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const { base, target } = await searchParams;
  if (!base || !target) {
    notFound();
  }

  const data = await getAnalysis(base, target);

  return (
    <main className="min-h-screen bg-[#f5f6f8] text-[#17191d]">
      <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="border-b border-[#d7dce2] pb-5">
          <div className="flex flex-wrap gap-3 text-sm font-semibold text-[#2563eb]">
            <Link className="hover:underline" href="/">
              검색
            </Link>
            <Link className="hover:underline" href={`/cases/${data.base.case_id}/compare`}>
              유사판례 후보
            </Link>
          </div>
          <div className="mt-4">
            <p className="text-sm font-semibold text-[#667085]">판례 비교</p>
            <h1 className="mt-1 text-2xl font-bold text-[#111827]">
              {data.base.case_no} vs {data.compare.case_no}
            </h1>
            <p className="mt-2 text-sm text-[#667085]">
              {data.analysis.generated_by}
              {data.analysis.fallback_used ? ` · ${data.analysis.fallback_reason}` : ""}
            </p>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-2">
          <CaseSummary label="기준 판례" item={data.base} />
          <CaseSummary label="비교 판례" item={data.compare} />
        </section>

        <section className="rounded-[8px] border-l-4 border-[#dc2626] bg-[#fff5f5] p-5">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-[#dc2626] text-xs font-bold text-white">!</span>
            <h2 className="text-sm font-bold text-[#991b1b]">결론 차이</h2>
          </div>
          <p className="mt-3 text-sm leading-6 text-[#1f2937]">{data.analysis.result_difference}</p>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <ClaimList items={data.analysis.common_points} title="공통점" />
          <DifferenceList items={data.analysis.material_differences} title="주요 차이점" />
          <TurningPointList items={data.analysis.turning_points} title="판단을 가른 지점" />
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <EvidenceList items={data.evidence_links.base} title="기준 판례 근거" />
          <EvidenceList items={data.evidence_links.compare} title="비교 판례 근거" />
        </section>

        <FeedbackForm baseCaseId={data.base.case_id} compareCaseId={data.compare.case_id} />

        <footer className="border-t border-[#d7dce2] pt-4 text-sm leading-6 text-[#667085]">
          {data.disclaimer}
        </footer>
      </div>
    </main>
  );
}

function CaseSummary({
  label,
  item,
}: {
  label: string;
  item: CompareAnalysis["base"];
}) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <p className="text-sm font-semibold text-[#2563eb]">{label}</p>
      <h2 className="mt-1 text-lg font-bold text-[#111827]">{item.case_no}</h2>
      <p className="mt-1 text-sm text-[#667085]">
        {item.court_name}
        {item.decision_date ? ` · ${item.decision_date}` : ""}
      </p>
      <p className="mt-3 text-sm leading-6 text-[#303846]">{formatOutcome(item.outcome)}</p>
    </section>
  );
}

function ClaimList({
  title,
  items,
}: {
  title: string;
  items: CompareAnalysis["analysis"]["common_points"];
}) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <h2 className="text-sm font-bold text-[#111827]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#303846]" key={item.text}>
              {item.text}
              <EvidenceIds ids={[...item.evidence_ids.base, ...item.evidence_ids.compare]} />
            </article>
          ))
        ) : (
          <p className="text-sm text-[#667085]">구조화된 공통점이 없습니다.</p>
        )}
      </div>
    </section>
  );
}

function DifferenceList({
  title,
  items,
}: {
  title: string;
  items: CompareAnalysis["analysis"]["material_differences"];
}) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <h2 className="text-sm font-bold text-[#111827]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#303846]" key={item.factor}>
              <p className="font-semibold text-[#111827]">{item.factor}</p>
              <p>기준 판례: {item.base}</p>
              <p>비교 판례: {item.compare}</p>
              <p className="mt-1 text-[#526070]">{item.meaning}</p>
            </article>
          ))
        ) : (
          <p className="text-sm text-[#667085]">구조화된 주요 차이점이 없습니다.</p>
        )}
      </div>
    </section>
  );
}

function TurningPointList({
  title,
  items,
}: {
  title: string;
  items: CompareAnalysis["analysis"]["turning_points"];
}) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <h2 className="text-sm font-bold text-[#111827]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#303846]" key={item.title}>
              <p className="font-semibold text-[#111827]">{item.title}</p>
              <p>{item.explanation}</p>
              <EvidenceIds ids={[...item.evidence_ids.base, ...item.evidence_ids.compare]} />
            </article>
          ))
        ) : (
          <p className="text-sm text-[#667085]">구조화된 판단 차이 지점이 없습니다.</p>
        )}
      </div>
    </section>
  );
}

function EvidenceList({
  title,
  items,
}: {
  title: string;
  items: CompareAnalysis["evidence_links"]["base"];
}) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <h2 className="text-sm font-bold text-[#111827]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#303846]" key={item.evidence_id}>
              <p className="font-mono text-xs text-[#667085]">
                {item.evidence_id} · {item.section_type}
              </p>
              <p className="mt-1">{item.text}</p>
            </article>
          ))
        ) : (
          <p className="text-sm text-[#667085]">연결된 근거가 없습니다.</p>
        )}
      </div>
    </section>
  );
}

function EvidenceIds({ ids }: { ids: string[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {ids.map((id) => (
        <span className="rounded-[5px] border border-[#d7dce2] px-2 py-1 text-xs text-[#465366]" key={id}>
          {id}
        </span>
      ))}
    </div>
  );
}
