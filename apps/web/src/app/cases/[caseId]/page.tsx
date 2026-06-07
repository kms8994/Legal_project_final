import Link from "next/link";
import { notFound } from "next/navigation";

const SEARCH_API_URL = process.env.SEARCH_API_URL ?? "http://localhost:8000";

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
    collected_at: string;
  };
  structure: {
    facts: string | null;
    legal_issue: string | null;
    court_reasoning: string | null;
    conclusion: string | null;
    material_facts: Record<string, unknown>;
    outcome: Record<string, unknown>;
    cited_articles: string[];
    facets: Record<string, unknown>;
    evidence_spans: Record<string, unknown>;
    confidence_score: number;
    review_status: string;
  };
  paragraphs: Array<{
    evidence_id: string;
    paragraph_id: string;
    section_type: string;
    paragraph_order: number;
    text: string;
    char_start: number | null;
    char_end: number | null;
  }>;
};

type CaseRagSummary = {
  summary: {
    facts: SummarySection;
    issue: SummarySection;
    reasoning: SummarySection;
    outcome: SummarySection;
    generated_by: string;
    fallback_used: boolean;
    fallback_reason: string | null;
  };
  evidence_links: Array<{
    evidence_id: string;
    section_type: string;
    text: string;
  }>;
  disclaimer: string;
};

type SummarySection = {
  title: string;
  text: string;
  evidence_ids: string[];
};

type CasePageProps = {
  params: Promise<{
    caseId: string;
  }>;
};

async function getCaseDetail(caseId: string): Promise<CaseDetail> {
  const response = await fetch(`${SEARCH_API_URL}/api/v1/cases/${caseId}`, {
    cache: "no-store",
  });

  if (response.status === 404) {
    notFound();
  }

  if (!response.ok) {
    throw new Error("판례 상세 요청에 실패했습니다.");
  }

  return response.json() as Promise<CaseDetail>;
}

async function getCaseRagSummary(caseId: string): Promise<CaseRagSummary | null> {
  const response = await fetch(`${SEARCH_API_URL}/api/v1/cases/${caseId}/rag-summary`, {
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  return response.json() as Promise<CaseRagSummary>;
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "예" : "아니오";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function displayKey(key: string): string {
  const labels: Record<string, string> = {
    direction: "판결 방향",
    disposition: "주문",
    key_factor: "주요 판단 요소",
    ratio_or_percentage: "비율",
    confidence: "신뢰도",
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
  return labels[key] ?? key;
}

export default async function CaseDetailPage({ params }: CasePageProps) {
  const { caseId } = await params;
  const [detail, ragSummary] = await Promise.all([
    getCaseDetail(caseId),
    getCaseRagSummary(caseId),
  ]);
  const materialFacts = Object.entries(detail.structure.material_facts);
  const outcome = Object.entries(detail.structure.outcome);

  return (
    <main className="min-h-screen bg-[#f5f6f8] text-[#17191d]">
      <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="border-b border-[#d7dce2] pb-5">
          <Link className="text-sm font-semibold text-[#2563eb] hover:underline" href="/">
            ← 검색으로 돌아가기
          </Link>
          <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-[#2563eb]">기준 판례</p>
              <h1 className="mt-1 text-2xl font-bold text-[#111827]">{detail.case.case_name}</h1>
              <p className="mt-2 text-sm text-[#667085]">
                {detail.case.case_no} · {detail.case.court_name}
                {detail.case.decision_date ? ` · ${detail.case.decision_date}` : ""}
              </p>
            </div>
            <div className="rounded-[6px] border border-[#d7dce2] bg-[#f8fafc] px-3 py-2 text-sm font-semibold text-[#465366]">
              신뢰도 {Math.round(detail.structure.confidence_score * 100)}% ·{" "}
              {reviewStatusLabel(detail.structure.review_status)}
            </div>
          </div>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-[#526070]">
            이 판례를 기준 판례로 삼아 사실관계가 유사한 후보 판례를 찾을 수 있습니다.
            후보를 선택하면 두 판례의 공통점, 차이점, 결론 차이를 비교합니다.
          </p>
          <Link
            className="mt-4 inline-flex rounded-[6px] bg-[#2563eb] px-4 py-2 text-sm font-bold text-white transition hover:bg-[#1d4ed8]"
            href={`/cases/${caseId}/compare`}
          >
            이 판례와 유사한 판례 찾기
          </Link>
        </header>

        {ragSummary ? (
          <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-[#667085]">근거 기반 요약</p>
                <h2 className="mt-1 text-xl font-bold text-[#111827]">판례 요약</h2>
              </div>
              <span className="rounded-[5px] bg-[#eff6ff] px-2 py-1 text-xs font-bold text-[#465366]">
                {ragSummary.summary.generated_by}
              </span>
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              <SummaryBlock section={ragSummary.summary.facts} />
              <SummaryBlock section={ragSummary.summary.issue} />
              <SummaryBlock section={ragSummary.summary.reasoning} />
              <SummaryBlock section={ragSummary.summary.outcome} />
            </div>
            <p className="mt-4 text-xs leading-5 text-[#667085]">{ragSummary.disclaimer}</p>
          </section>
        ) : null}

        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid gap-4">
            <Panel title="사실관계" value={detail.structure.facts} />
            <Panel title="법적 쟁점" value={detail.structure.legal_issue} />
            <Panel title="법원의 판단" value={detail.structure.court_reasoning} />
            <Panel title="결론" value={detail.structure.conclusion} />
          </div>

          <aside className="grid content-start gap-4">
            <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-[#111827]">사건 정보</h2>
              <dl className="mt-3 grid gap-2 text-sm">
                <MetaRow label="분야" value={detail.case.legal_domain} />
                <MetaRow label="사건유형" value={detail.case.case_type} />
                <MetaRow label="심급" value={detail.case.court_level} />
                <MetaRow label="외부 ID" value={detail.case.external_id} />
              </dl>
              <a
                className="mt-4 inline-flex text-sm font-semibold text-[#2563eb] hover:underline"
                href={detail.case.source_url && !detail.case.source_url.includes("/DRF/") ? detail.case.source_url : `https://www.law.go.kr/LSW/precSc.do?menuId=7&subMenuId=47&tabMenuId=213&query=${encodeURIComponent(detail.case.case_no)}`}
                rel="noreferrer"
                target="_blank"
              >
                공식 원문 열기
              </a>
            </section>

            <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
              <h2 className="text-sm font-bold text-[#111827]">인용 조문</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {detail.structure.cited_articles.length > 0 ? (
                  detail.structure.cited_articles.map((article) => (
                    <span className="rounded-[5px] border border-[#d7dce2] px-2.5 py-1 text-xs text-[#4b5563]" key={article}>
                      {article}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-[#667085]">인용 조문이 없습니다.</p>
                )}
              </div>
            </section>
          </aside>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <KeyValuePanel items={materialFacts} title="주요 사실" />
          <KeyValuePanel items={outcome} title="판결 결과" />
        </section>

        <section className="border-t border-[#d7dce2] pt-5">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[#667085]">근거</p>
              <h2 className="text-xl font-bold text-[#111827]">원문 문단</h2>
            </div>
            <p className="text-sm font-semibold text-[#465366]">{detail.paragraphs.length}개 문단</p>
          </div>

          <div className="grid gap-3">
            {detail.paragraphs.length > 0 ? (
              detail.paragraphs.map((paragraph) => (
                <article className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm" key={paragraph.paragraph_id}>
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-[#667085]">
                    <span className="font-mono text-[#2563eb]">{paragraph.evidence_id}</span>
                    <span>{paragraph.section_type}</span>
                    <span>순서 {paragraph.paragraph_order}</span>
                  </div>
                  <p className="text-sm leading-6 text-[#303846]">{paragraph.text}</p>
                </article>
              ))
            ) : (
              <div className="rounded-[8px] border border-dashed border-[#b9c2cf] bg-white p-5 text-sm text-[#667085]">
                이 판례의 근거 문단이 아직 없습니다.
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function SummaryBlock({ section }: { section: SummarySection }) {
  return (
    <article className="rounded-[6px] border border-[#e5eaf0] bg-[#fbfcfe] p-4">
      <h3 className="text-sm font-bold text-[#111827]">{section.title}</h3>
      <p className="mt-2 text-sm leading-6 text-[#303846]">{section.text}</p>
      {section.evidence_ids.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {section.evidence_ids.map((id) => (
            <span className="rounded-[5px] border border-[#d7dce2] px-2 py-1 text-xs text-[#465366]" key={id}>
              {id}
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function Panel({ title, value }: { title: string; value: string | null }) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <h2 className="text-sm font-bold text-[#111827]">{title}</h2>
      <p className="mt-3 text-sm leading-6 text-[#303846]">{value || "표시할 데이터가 없습니다."}</p>
    </section>
  );
}

function MetaRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="grid grid-cols-[96px_1fr] gap-2">
      <dt className="text-[#667085]">{label}</dt>
      <dd className="font-medium text-[#303846]">{value || "-"}</dd>
    </div>
  );
}

function KeyValuePanel({ title, items }: { title: string; items: Array<[string, unknown]> }) {
  return (
    <section className="rounded-[8px] border border-[#d7dce2] bg-white p-5 shadow-sm">
      <h2 className="text-sm font-bold text-[#111827]">{title}</h2>
      <dl className="mt-3 grid gap-2 text-sm">
        {items.length > 0 ? (
          items.map(([key, value]) => (
            <div className="grid gap-1 border-b border-[#e5eaf0] pb-2 last:border-b-0" key={key}>
              <dt className="text-xs font-semibold text-[#667085]">{displayKey(key)}</dt>
              <dd className="text-[#303846]">{displayValue(value)}</dd>
            </div>
          ))
        ) : (
          <p className="text-[#667085]">구조화된 데이터가 없습니다.</p>
        )}
      </dl>
    </section>
  );
}

function reviewStatusLabel(status: string) {
  if (status === "auto_validated") return "자동 검증";
  if (status === "needs_review") return "검토 필요";
  return status;
}
