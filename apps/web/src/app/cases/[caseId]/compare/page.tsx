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
    throw new Error("Compare candidate request failed.");
  }

  return response.json() as Promise<CompareCandidates>;
}

export default async function CompareCandidatesPage({ params }: ComparePageProps) {
  const { caseId } = await params;
  const data = await getCompareCandidates(caseId);

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#191a17]">
      <div className="mx-auto grid w-full max-w-6xl gap-6 px-5 py-6 sm:px-8 lg:px-10">
        <header className="border-b border-[#d8d8cf] pb-5">
          <div className="flex flex-wrap gap-3 text-sm font-medium text-[#44615a]">
            <Link className="hover:underline" href="/">
              Search
            </Link>
            <Link className="hover:underline" href={`/cases/${caseId}`}>
              Case detail
            </Link>
          </div>
          <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase text-[#6d7165]">Compare candidates</p>
              <h1 className="mt-1 text-2xl font-semibold">{data.base_case.case_no}</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-[#555950]">
                {data.base_case.summary_card || "No base summary is available."}
              </p>
            </div>
            <div className="border border-[#c7c8bd] bg-white px-3 py-2 text-sm text-[#4d534a]">
              {data.ranking_policy.policy_name}
            </div>
          </div>
        </header>

        <section className="grid gap-3">
          {data.candidates.length > 0 ? (
            data.candidates.map((candidate, index) => (
              <article className="border border-[#d3d4ca] bg-white p-4" key={candidate.case_id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-xs uppercase text-[#6d7165]">
                      Candidate {index + 1}
                    </p>
                    <h2 className="mt-1 text-lg font-semibold">{candidate.case_name}</h2>
                    <p className="mt-1 text-sm text-[#666b61]">
                      {candidate.case_no} · {candidate.court_name}
                      {candidate.decision_date ? ` · ${candidate.decision_date}` : ""}
                    </p>
                  </div>
                  <div className="border border-[#d3d4ca] px-3 py-2 text-sm text-[#30332d]">
                    Score {Math.round(candidate.scores.final_score * 100)}%
                  </div>
                </div>

                <p className="mt-3 text-sm leading-6 text-[#30332d]">{candidate.summary_card}</p>

                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <Score label="Material facts" value={candidate.scores.material_fact_match} />
                  <Score label="Statute overlap" value={candidate.scores.statute_overlap} />
                  <Score label="Facet match" value={candidate.scores.facet_match_score} />
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <ListBlock items={candidate.common_facts} title="Common facts" />
                  <ListBlock items={candidate.possible_turning_points} title="Possible differences" />
                </div>

                <div className="mt-4 border-t border-[#eeeeea] pt-3">
                  <p className="text-sm font-medium text-[#5b5f55]">Outcome difference</p>
                  <p className="mt-1 text-sm leading-6 text-[#30332d]">
                    {candidate.outcome_difference_summary}
                  </p>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {candidate.evidence_ids.map((id) => (
                    <span className="bg-[#f2eadf] px-2 py-1 text-xs text-[#555950]" key={id}>
                      Evidence {id}
                    </span>
                  ))}
                  <Link
                    className="text-sm font-semibold text-[#1f3d36] hover:underline"
                    href={`/compare?base=${caseId}&target=${candidate.case_id}`}
                  >
                    Compare
                  </Link>
                  <Link
                    className="ml-auto text-sm font-semibold text-[#1f3d36] hover:underline"
                    href={`/cases/${candidate.case_id}`}
                  >
                    Open detail
                  </Link>
                </div>
              </article>
            ))
          ) : (
            <div className="border border-[#d3d4ca] bg-white p-5 text-sm text-[#555950]">
              No comparison candidates were found.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="border border-[#eeeeea] p-3">
      <p className="text-xs uppercase text-[#666b61]">{label}</p>
      <p className="mt-1 text-lg font-semibold">{Math.round(value * 100)}%</p>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="border border-[#eeeeea] p-3">
      <h3 className="text-sm font-semibold text-[#5b5f55]">{title}</h3>
      {items.length > 0 ? (
        <ul className="mt-2 grid gap-1 text-sm text-[#30332d]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-[#666b61]">No structured signal.</p>
      )}
    </section>
  );
}
