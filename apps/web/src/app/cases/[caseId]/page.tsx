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
    throw new Error("Case detail request failed.");
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
    return value ? "true" : "false";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
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
    <main className="min-h-screen bg-[#f7f7f4] text-[#191a17]">
      <div className="mx-auto grid w-full max-w-6xl gap-6 px-5 py-6 sm:px-8 lg:px-10">
        <header className="border-b border-[#d8d8cf] pb-5">
          <Link className="text-sm font-medium text-[#44615a] hover:underline" href="/">
            Back to search
          </Link>
          <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase text-[#6d7165]">Case detail</p>
              <h1 className="mt-1 text-2xl font-semibold">{detail.case.case_name}</h1>
              <p className="mt-2 text-sm text-[#5b5f55]">
                {detail.case.case_no} · {detail.case.court_name}
                {detail.case.decision_date ? ` · ${detail.case.decision_date}` : ""}
              </p>
            </div>
            <div className="border border-[#c7c8bd] bg-white px-3 py-2 text-sm text-[#4d534a]">
              Confidence {Math.round(detail.structure.confidence_score * 100)}% ·{" "}
              {detail.structure.review_status}
            </div>
          </div>
          <Link
            className="mt-4 inline-flex bg-[#1f3d36] px-4 py-2 text-sm font-semibold text-white hover:bg-[#17312b]"
            href={`/cases/${caseId}/compare`}
          >
            View compare candidates
          </Link>
        </header>

        {ragSummary ? (
          <section className="border border-[#d3d4ca] bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-mono text-xs uppercase text-[#6d7165]">Grounded summary</p>
                <h2 className="mt-1 text-xl font-semibold">RAG case summary</h2>
              </div>
              <span className="bg-[#eef0e8] px-2 py-1 text-xs text-[#4d534a]">
                {ragSummary.summary.generated_by}
              </span>
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              <SummaryBlock section={ragSummary.summary.facts} />
              <SummaryBlock section={ragSummary.summary.issue} />
              <SummaryBlock section={ragSummary.summary.reasoning} />
              <SummaryBlock section={ragSummary.summary.outcome} />
            </div>
            <p className="mt-4 text-xs leading-5 text-[#666b61]">{ragSummary.disclaimer}</p>
          </section>
        ) : null}

        <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid gap-4">
            <Panel title="Facts" value={detail.structure.facts} />
            <Panel title="Legal issue" value={detail.structure.legal_issue} />
            <Panel title="Court reasoning" value={detail.structure.court_reasoning} />
            <Panel title="Conclusion" value={detail.structure.conclusion} />
          </div>

          <aside className="grid content-start gap-4">
            <section className="border border-[#d3d4ca] bg-white p-4">
              <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">Source</h2>
              <dl className="mt-3 grid gap-2 text-sm">
                <MetaRow label="Domain" value={detail.case.legal_domain} />
                <MetaRow label="Type" value={detail.case.case_type} />
                <MetaRow label="Level" value={detail.case.court_level} />
                <MetaRow label="External ID" value={detail.case.external_id} />
              </dl>
              {detail.case.source_url ? (
                <a
                  className="mt-4 inline-flex text-sm font-medium text-[#44615a] hover:underline"
                  href={detail.case.source_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open official source
                </a>
              ) : null}
            </section>

            <section className="border border-[#d3d4ca] bg-white p-4">
              <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">Cited articles</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {detail.structure.cited_articles.length > 0 ? (
                  detail.structure.cited_articles.map((article) => (
                    <span className="border border-[#d3d4ca] px-2 py-1 text-xs" key={article}>
                      {article}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-[#666b61]">No cited articles.</p>
                )}
              </div>
            </section>
          </aside>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <KeyValuePanel items={materialFacts} title="Material facts" />
          <KeyValuePanel items={outcome} title="Outcome" />
        </section>

        <section className="border-t border-[#d8d8cf] pt-5">
          <div className="mb-3 flex items-end justify-between gap-3">
            <div>
              <p className="font-mono text-xs uppercase text-[#6d7165]">Evidence</p>
              <h2 className="text-xl font-semibold">Source paragraphs</h2>
            </div>
            <p className="text-sm text-[#666b61]">{detail.paragraphs.length} paragraphs</p>
          </div>

          <div className="grid gap-3">
            {detail.paragraphs.length > 0 ? (
              detail.paragraphs.map((paragraph) => (
                <article className="border border-[#d3d4ca] bg-white p-4" key={paragraph.paragraph_id}>
                  <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-[#666b61]">
                    <span className="font-mono text-[#1f3d36]">{paragraph.evidence_id}</span>
                    <span>{paragraph.section_type}</span>
                    <span>order {paragraph.paragraph_order}</span>
                  </div>
                  <p className="text-sm leading-6 text-[#30332d]">{paragraph.text}</p>
                </article>
              ))
            ) : (
              <div className="border border-[#d3d4ca] bg-white p-4 text-sm text-[#666b61]">
                No evidence paragraphs are available for this case yet.
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
    <article className="border-t border-[#eeeeea] pt-3">
      <h3 className="text-sm font-semibold uppercase text-[#5b5f55]">{section.title}</h3>
      <p className="mt-2 text-sm leading-6 text-[#30332d]">{section.text}</p>
      {section.evidence_ids.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {section.evidence_ids.map((id) => (
            <span className="bg-[#f2eadf] px-2 py-1 text-xs text-[#5c5140]" key={id}>
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
    <section className="border border-[#d3d4ca] bg-white p-4">
      <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">{title}</h2>
      <p className="mt-3 text-sm leading-6 text-[#30332d]">{value || "No data available."}</p>
    </section>
  );
}

function MetaRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="grid grid-cols-[96px_1fr] gap-2">
      <dt className="text-[#666b61]">{label}</dt>
      <dd className="font-medium text-[#30332d]">{value || "-"}</dd>
    </div>
  );
}

function KeyValuePanel({ title, items }: { title: string; items: Array<[string, unknown]> }) {
  return (
    <section className="border border-[#d3d4ca] bg-white p-4">
      <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">{title}</h2>
      <dl className="mt-3 grid gap-2 text-sm">
        {items.length > 0 ? (
          items.map(([key, value]) => (
            <div className="grid gap-1 border-b border-[#eeeeea] pb-2 last:border-b-0" key={key}>
              <dt className="font-mono text-xs text-[#666b61]">{key}</dt>
              <dd className="text-[#30332d]">{displayValue(value)}</dd>
            </div>
          ))
        ) : (
          <p className="text-[#666b61]">No structured data.</p>
        )}
      </dl>
    </section>
  );
}
