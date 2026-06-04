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
    throw new Error("Compare analysis request failed.");
  }

  return response.json() as Promise<CompareAnalysis>;
}

function formatOutcome(outcome: Record<string, unknown>): string {
  const entries = Object.entries(outcome);
  if (entries.length === 0) {
    return "No structured outcome.";
  }
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(" · ");
}

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const { base, target } = await searchParams;
  if (!base || !target) {
    notFound();
  }

  const data = await getAnalysis(base, target);

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#191a17]">
      <div className="mx-auto grid w-full max-w-6xl gap-6 px-5 py-6 sm:px-8 lg:px-10">
        <header className="border-b border-[#d8d8cf] pb-5">
          <div className="flex flex-wrap gap-3 text-sm font-medium text-[#44615a]">
            <Link className="hover:underline" href="/">
              Search
            </Link>
            <Link className="hover:underline" href={`/cases/${data.base.case_id}/compare`}>
              Candidates
            </Link>
          </div>
          <div className="mt-4">
            <p className="font-mono text-xs uppercase text-[#6d7165]">Comparison analysis</p>
            <h1 className="mt-1 text-2xl font-semibold">
              {data.base.case_no} vs {data.compare.case_no}
            </h1>
            <p className="mt-2 text-sm text-[#666b61]">
              {data.analysis.generated_by}
              {data.analysis.fallback_used ? ` · ${data.analysis.fallback_reason}` : ""}
            </p>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-2">
          <CaseSummary label="Base" item={data.base} />
          <CaseSummary label="Compare" item={data.compare} />
        </section>

        <section className="border border-[#d3d4ca] bg-white p-4">
          <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">Result difference</h2>
          <p className="mt-3 text-sm leading-6 text-[#30332d]">{data.analysis.result_difference}</p>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <ClaimList items={data.analysis.common_points} title="Common points" />
          <DifferenceList items={data.analysis.material_differences} title="Material differences" />
          <TurningPointList items={data.analysis.turning_points} title="Turning points" />
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <EvidenceList items={data.evidence_links.base} title="Base evidence" />
          <EvidenceList items={data.evidence_links.compare} title="Compare evidence" />
        </section>

        <FeedbackForm baseCaseId={data.base.case_id} compareCaseId={data.compare.case_id} />

        <footer className="border-t border-[#d8d8cf] pt-4 text-sm leading-6 text-[#666b61]">
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
    <section className="border border-[#d3d4ca] bg-white p-4">
      <p className="font-mono text-xs uppercase text-[#6d7165]">{label}</p>
      <h2 className="mt-1 text-lg font-semibold">{item.case_no}</h2>
      <p className="mt-1 text-sm text-[#666b61]">
        {item.court_name}
        {item.decision_date ? ` · ${item.decision_date}` : ""}
      </p>
      <p className="mt-3 text-sm leading-6 text-[#30332d]">{formatOutcome(item.outcome)}</p>
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
    <section className="border border-[#d3d4ca] bg-white p-4">
      <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#30332d]" key={item.text}>
              {item.text}
              <EvidenceIds ids={[...item.evidence_ids.base, ...item.evidence_ids.compare]} />
            </article>
          ))
        ) : (
          <p className="text-sm text-[#666b61]">No structured common point.</p>
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
    <section className="border border-[#d3d4ca] bg-white p-4">
      <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#30332d]" key={item.factor}>
              <p className="font-semibold">{item.factor}</p>
              <p>Base: {item.base}</p>
              <p>Compare: {item.compare}</p>
              <p className="mt-1 text-[#555950]">{item.meaning}</p>
            </article>
          ))
        ) : (
          <p className="text-sm text-[#666b61]">No structured material difference.</p>
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
    <section className="border border-[#d3d4ca] bg-white p-4">
      <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#30332d]" key={item.title}>
              <p className="font-semibold">{item.title}</p>
              <p>{item.explanation}</p>
              <EvidenceIds ids={[...item.evidence_ids.base, ...item.evidence_ids.compare]} />
            </article>
          ))
        ) : (
          <p className="text-sm text-[#666b61]">No structured turning point.</p>
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
    <section className="border border-[#d3d4ca] bg-white p-4">
      <h2 className="text-sm font-semibold uppercase text-[#5b5f55]">{title}</h2>
      <div className="mt-3 grid gap-3">
        {items.length > 0 ? (
          items.map((item) => (
            <article className="text-sm leading-6 text-[#30332d]" key={item.evidence_id}>
              <p className="font-mono text-xs text-[#1f3d36]">
                {item.evidence_id} · {item.section_type}
              </p>
              <p className="mt-1">{item.text}</p>
            </article>
          ))
        ) : (
          <p className="text-sm text-[#666b61]">No evidence link.</p>
        )}
      </div>
    </section>
  );
}

function EvidenceIds({ ids }: { ids: string[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {ids.map((id) => (
        <span className="bg-[#f2eadf] px-2 py-1 text-xs text-[#555950]" key={id}>
          {id}
        </span>
      ))}
    </div>
  );
}
