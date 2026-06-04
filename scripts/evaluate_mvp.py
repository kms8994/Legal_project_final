from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SEARCH_API = ROOT / "apps" / "search-api"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SEARCH_API) not in sys.path:
    sys.path.insert(0, str(SEARCH_API))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@dataclass(frozen=True)
class StatuteEvalCase:
    eval_id: str
    query: str
    expected_ref: str
    intent: str


@dataclass(frozen=True)
class NaturalEvalCase:
    eval_id: str
    query: str
    expected_terms: list[str]
    expected_articles: list[str]
    intent: str


STATUTE_CASES = [
    StatuteEvalCase("S01", "민법 제750조", "민법_제750조", "불법행위 손해배상 일반"),
    StatuteEvalCase("S02", "민법 제751조", "민법_제751조", "위자료 및 정신적 손해"),
    StatuteEvalCase("S03", "민법 제396조", "민법_제396조", "과실상계"),
    StatuteEvalCase("S04", "민법 제393조", "민법_제393조", "손해배상 범위"),
    StatuteEvalCase("S05", "민법 제763조", "민법_제763조", "불법행위 손해배상 준용"),
    StatuteEvalCase("S06", "민법 제766조", "민법_제766조", "손해배상청구권 소멸시효"),
    StatuteEvalCase("S07", "민법 제756조", "민법_제756조", "사용자책임"),
    StatuteEvalCase("S08", "민법 제760조", "민법_제760조", "공동불법행위"),
    StatuteEvalCase("S09", "민법 750", "민법_제750조", "약식 조문 입력 정규화"),
    StatuteEvalCase("S10", "자동차손해배상 보장법 제3조", "자동차손해배상_보장법_제3조", "자동차 사고 손해배상 책임"),
]


NATURAL_CASES = [
    NaturalEvalCase(
        "N01",
        "교통사고 피해자의 무단횡단과 과실상계가 문제된 손해배상 판례",
        ["교통사고", "무단횡단", "과실상계", "손해배상"],
        ["민법_제396조", "민법_제750조"],
        "교통사고 과실상계",
    ),
    NaturalEvalCase(
        "N02",
        "운전자가 전방주시의무를 위반해 보행자를 다치게 한 사건",
        ["전방주시", "보행자", "교통사고", "과실"],
        ["민법_제750조"],
        "운전자 주의의무 위반",
    ),
    NaturalEvalCase(
        "N03",
        "자동차 운행자 책임과 보험자의 손해배상 책임이 문제된 판례",
        ["자동차", "운행자", "보험", "손해배상"],
        ["자동차손해배상_보장법_제3조"],
        "자동차손해배상 보장법 책임",
    ),
    NaturalEvalCase(
        "N04",
        "피해자에게도 일부 잘못이 있어 배상액이 줄어든 사건",
        ["피해자", "과실", "배상액", "감액"],
        ["민법_제396조"],
        "피해자 과실과 감액",
    ),
    NaturalEvalCase(
        "N05",
        "위자료 액수가 어떻게 정해지는지 문제된 손해배상 판례",
        ["위자료", "정신적", "손해", "배상"],
        ["민법_제751조"],
        "위자료 산정",
    ),
    NaturalEvalCase(
        "N06",
        "회사 직원이 업무 중 사고를 내서 사용자 책임이 문제된 사건",
        ["회사", "직원", "업무", "사용자책임"],
        ["민법_제756조"],
        "사용자책임",
    ),
    NaturalEvalCase(
        "N07",
        "여러 사람이 함께 손해를 발생시킨 공동불법행위 판례",
        ["공동", "불법행위", "손해", "여러"],
        ["민법_제760조"],
        "공동불법행위",
    ),
    NaturalEvalCase(
        "N08",
        "사고와 손해 사이의 인과관계가 다투어진 판례",
        ["사고", "손해", "인과관계"],
        ["민법_제750조"],
        "인과관계",
    ),
    NaturalEvalCase(
        "N09",
        "손해배상청구권 소멸시효가 문제된 판례",
        ["손해배상청구권", "소멸시효"],
        ["민법_제766조"],
        "소멸시효",
    ),
    NaturalEvalCase(
        "N10",
        "통상손해와 특별손해의 배상 범위가 문제된 판례",
        ["통상손해", "특별손해", "배상", "범위"],
        ["민법_제393조"],
        "손해배상 범위",
    ),
]


def post_json(client: TestClient, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any], float]:
    started = perf_counter()
    response = client.post(path, json=payload)
    elapsed_ms = (perf_counter() - started) * 1000
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - report raw API failures.
        body = {"raw": response.text}
    return response.status_code, body, elapsed_ms


def get_json(client: TestClient, path: str) -> tuple[int, dict[str, Any], float]:
    started = perf_counter()
    response = client.get(path)
    elapsed_ms = (perf_counter() - started) * 1000
    try:
        body = response.json()
    except Exception:  # noqa: BLE001 - report raw API failures.
        body = {"raw": response.text}
    return response.status_code, body, elapsed_ms


def result_text(result: dict[str, Any]) -> str:
    snippets = " ".join(snippet.get("text", "") for snippet in result.get("evidence_snippets", []))
    parts = [
        result.get("case_no", ""),
        result.get("case_name", ""),
        result.get("summary_card", ""),
        " ".join(result.get("cited_articles", [])),
        json.dumps(result.get("outcome", {}), ensure_ascii=False),
        snippets,
    ]
    return " ".join(str(part) for part in parts).lower()


def is_natural_relevant(result: dict[str, Any], case: NaturalEvalCase) -> bool:
    text = result_text(result)
    article_hit = bool(set(case.expected_articles) & set(result.get("cited_articles", [])))
    term_hits = sum(1 for term in case.expected_terms if term.lower() in text)
    required_hits = 1 if len(case.expected_terms) <= 2 else 2
    return article_hit or term_hits >= required_hits


def evaluate_statute(client: TestClient, size: int) -> dict[str, Any]:
    rows = []
    latencies = []
    precisions = []
    top1_hits = 0
    failures = 0

    for case in STATUTE_CASES:
        status, body, elapsed_ms = post_json(
            client,
            "/api/v1/search/statute",
            {"query": case.query, "page": 1, "size": size, "sort": "relevance"},
        )
        latencies.append(elapsed_ms)
        results = body.get("results", []) if status == 200 else []
        hits = [
            index + 1
            for index, result in enumerate(results)
            if case.expected_ref in result.get("cited_articles", [])
        ]
        precision = len(hits) / len(results) if results else 0.0
        precisions.append(precision)
        if hits and hits[0] == 1:
            top1_hits += 1
        if status != 200:
            failures += 1
        rows.append(
            {
                "id": case.eval_id,
                "query": case.query,
                "expected_ref": case.expected_ref,
                "status": status,
                "result_count": len(results),
                "precision_at_k": round(precision, 3),
                "first_hit_rank": hits[0] if hits else None,
                "latency_ms": round(elapsed_ms, 1),
                "top_results": compact_results(results[:5]),
            }
        )

    return {
        "metric": {
            "query_count": len(STATUTE_CASES),
            "failures": failures,
            "precision_at_10": round(statistics.mean(precisions), 3) if precisions else 0.0,
            "top1_exact_article_rate": round(top1_hits / len(STATUTE_CASES), 3),
            "p95_latency_ms": percentile(latencies, 95),
        },
        "rows": rows,
    }


def evaluate_natural(client: TestClient, size: int) -> dict[str, Any]:
    rows = []
    latencies = []
    relevant_counts = []
    failures = 0
    base_case_ids: list[str] = []

    for case in NATURAL_CASES:
        status, body, elapsed_ms = post_json(
            client,
            "/api/v1/search/natural",
            {"query": case.query, "page": 1, "size": size},
        )
        latencies.append(elapsed_ms)
        results = body.get("results", []) if status == 200 else []
        relevance = [is_natural_relevant(result, case) for result in results[:5]]
        relevant_count = sum(1 for value in relevance if value)
        relevant_counts.append(relevant_count)
        if status != 200:
            failures += 1
        if results:
            base_case_ids.append(results[0]["case_id"])
        rows.append(
            {
                "id": case.eval_id,
                "query": case.query,
                "expected_terms": case.expected_terms,
                "expected_articles": case.expected_articles,
                "status": status,
                "result_count": len(results),
                "top5_relevant_count": relevant_count,
                "latency_ms": round(elapsed_ms, 1),
                "parsed_intent": body.get("parsed_intent"),
                "top_results": compact_results(results[:5], relevance),
            }
        )

    return {
        "metric": {
            "query_count": len(NATURAL_CASES),
            "failures": failures,
            "avg_top5_relevant_count": round(statistics.mean(relevant_counts), 3)
            if relevant_counts
            else 0.0,
            "p95_latency_ms": percentile(latencies, 95),
        },
        "rows": rows,
        "base_case_ids": unique(base_case_ids)[:10],
    }


def evaluate_compare(client: TestClient, base_case_ids: list[str], limit: int) -> dict[str, Any]:
    rows = []
    latencies = []
    material_scores: list[float] = []
    fact_scores: list[float] = []
    issue_scores: list[float] = []
    evidence_covered = 0
    candidate_total = 0
    failures = 0

    for base_case_id in base_case_ids:
        status, body, elapsed_ms = get_json(
            client,
            f"/api/v1/cases/{base_case_id}/compare-candidates?limit={limit}&require_outcome_difference=false",
        )
        latencies.append(elapsed_ms)
        candidates = body.get("candidates", []) if status == 200 else []
        if status != 200:
            failures += 1
        for candidate in candidates:
            scores = candidate.get("scores", {})
            material_scores.append(float(scores.get("material_fact_match", 0.0)))
            fact_scores.append(float(scores.get("facts_vector_similarity", 0.0)))
            issue_scores.append(float(scores.get("issue_similarity", 0.0)))
            candidate_total += 1
            if candidate.get("evidence_ids"):
                evidence_covered += 1
        rows.append(
            {
                "base_case_id": base_case_id,
                "status": status,
                "candidate_count": len(candidates),
                "latency_ms": round(elapsed_ms, 1),
                "base_case": body.get("base_case"),
                "top_candidates": compact_candidates(candidates),
            }
        )

    return {
        "metric": {
            "base_case_count": len(base_case_ids),
            "failures": failures,
            "avg_material_fact_match": rounded_mean(material_scores),
            "avg_facts_vector_similarity": rounded_mean(fact_scores),
            "avg_issue_similarity": rounded_mean(issue_scores),
            "evidence_coverage_rate": round(evidence_covered / candidate_total, 3)
            if candidate_total
            else 0.0,
            "p95_latency_ms": percentile(latencies, 95),
        },
        "rows": rows,
    }


def db_quality_snapshot() -> dict[str, Any]:
    with engine.connect() as connection:
        cases = connection.exec_driver_sql("select count(*) from cases").scalar_one()
        paragraphs = connection.exec_driver_sql("select count(*) from case_paragraphs").scalar_one()
        structures = connection.exec_driver_sql("select count(*) from case_structures").scalar_one()
        embeddings = connection.exec_driver_sql("select count(*) from case_embeddings").scalar_one()
        review_rows = connection.exec_driver_sql(
            """
            select review_status, count(*)
            from case_structures
            group by review_status
            order by review_status
            """
        ).all()
    review_counts = {row[0]: row[1] for row in review_rows}
    total_reviewed = sum(review_counts.values())
    return {
        "cases": cases,
        "paragraphs": paragraphs,
        "structures": structures,
        "embeddings": embeddings,
        "review_status": review_counts,
        "needs_review_rate": round(review_counts.get("needs_review", 0) / total_reviewed, 3)
        if total_reviewed
        else 0.0,
    }


def compact_results(results: list[dict[str, Any]], relevance: list[bool] | None = None) -> list[dict[str, Any]]:
    rows = []
    for index, result in enumerate(results):
        row = {
            "rank": index + 1,
            "case_id": result.get("case_id"),
            "case_no": result.get("case_no"),
            "case_name": result.get("case_name"),
            "decision_date": result.get("decision_date"),
            "score": result.get("score"),
            "review_status": result.get("review_status"),
            "cited_articles": result.get("cited_articles", []),
            "summary_card": result.get("summary_card", ""),
        }
        if relevance is not None:
            row["heuristic_relevant"] = relevance[index] if index < len(relevance) else False
        rows.append(row)
    return rows


def compact_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, candidate in enumerate(candidates[:5]):
        scores = candidate.get("scores", {})
        rows.append(
            {
                "rank": index + 1,
                "case_id": candidate.get("case_id"),
                "case_no": candidate.get("case_no"),
                "case_name": candidate.get("case_name"),
                "final_score": scores.get("final_score"),
                "facts_vector_similarity": scores.get("facts_vector_similarity"),
                "material_fact_match": scores.get("material_fact_match"),
                "issue_similarity": scores.get("issue_similarity"),
                "outcome_difference": scores.get("outcome_difference"),
                "evidence_count": len(candidate.get("evidence_ids", [])),
            }
        )
    return rows


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def rounded_mean(values: list[float]) -> float:
    return round(statistics.mean(values), 3) if values else 0.0


def percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return round(ordered[index], 1)


def json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def markdown_report(report: dict[str, Any]) -> str:
    statute = report["statute"]["metric"]
    natural = report["natural"]["metric"]
    compare = report["compare"]["metric"]
    db = report["db_snapshot"]

    lines = [
        "# MVP Evaluation Run",
        "",
        f"- Generated at: `{report['generated_at']}`",
        "- Labeling mode: heuristic first pass. Use top results below for manual confirmation.",
        "",
        "## Summary",
        "",
        "| Area | Metric | Value |",
        "|------|--------|-------|",
        f"| Statute search | precision@10 | {statute['precision_at_10']} |",
        f"| Statute search | top1 exact article rate | {statute['top1_exact_article_rate']} |",
        f"| Natural search | avg Top-5 relevant count | {natural['avg_top5_relevant_count']} |",
        f"| Compare candidates | avg material fact match | {compare['avg_material_fact_match']} |",
        f"| Compare candidates | evidence coverage rate | {compare['evidence_coverage_rate']} |",
        f"| Structure validation | needs_review rate | {db['needs_review_rate']} |",
        "",
        "## DB Snapshot",
        "",
        f"- Cases: {db['cases']}",
        f"- Paragraphs: {db['paragraphs']}",
        f"- Structures: {db['structures']}",
        f"- Embeddings: {db['embeddings']}",
        f"- Review status: `{json.dumps(db['review_status'], ensure_ascii=False)}`",
        "",
        "## Statute Search",
        "",
        "| ID | Query | Expected | Status | P@10 | First Hit | Top Result |",
        "|----|-------|----------|--------|------|-----------|------------|",
    ]
    for row in report["statute"]["rows"]:
        top = row["top_results"][0] if row["top_results"] else {}
        lines.append(
            "| {id} | {query} | {expected_ref} | {status} | {precision_at_k} | {first_hit_rank} | {top} |".format(
                id=row["id"],
                query=row["query"],
                expected_ref=row["expected_ref"],
                status=row["status"],
                precision_at_k=row["precision_at_k"],
                first_hit_rank=row["first_hit_rank"],
                top=md_escape(top.get("case_no", "")),
            )
        )

    lines.extend(
        [
            "",
            "## Natural Search",
            "",
            "| ID | Query | Status | Top-5 Relevant | Top Result |",
            "|----|-------|--------|----------------|------------|",
        ]
    )
    for row in report["natural"]["rows"]:
        top = row["top_results"][0] if row["top_results"] else {}
        lines.append(
            "| {id} | {query} | {status} | {count} | {top} |".format(
                id=row["id"],
                query=md_escape(row["query"]),
                status=row["status"],
                count=row["top5_relevant_count"],
                top=md_escape(top.get("case_no", "")),
            )
        )

    lines.extend(
        [
            "",
            "## Compare Candidates",
            "",
            "| Base Case | Status | Candidates | Top Candidate | Top Material Match |",
            "|-----------|--------|------------|---------------|--------------------|",
        ]
    )
    for row in report["compare"]["rows"]:
        top = row["top_candidates"][0] if row["top_candidates"] else {}
        lines.append(
            "| {base} | {status} | {count} | {top} | {material} |".format(
                base=row["base_case_id"],
                status=row["status"],
                count=row["candidate_count"],
                top=md_escape(top.get("case_no", "")),
                material=top.get("material_fact_match", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Next Manual Checks",
            "",
            "- Confirm whether each natural-search Top-5 result is actually relevant, not only keyword-matched.",
            "- Inspect 20 `needs_review` structures and classify the failure reason.",
            "- Review compare candidates with high vector similarity but low material fact match.",
            "",
            "Full machine-readable output is in `docs/evaluation_run.json`.",
        ]
    )
    return "\n".join(lines) + "\n"


def md_escape(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CaseLens MVP evaluation smoke metrics.")
    parser.add_argument("--json-output", default="docs/evaluation_run.json")
    parser.add_argument("--markdown-output", default="docs/EvaluationRun.md")
    parser.add_argument("--search-size", type=int, default=10)
    parser.add_argument("--compare-limit", type=int, default=5)
    args = parser.parse_args()

    client = TestClient(app)
    statute = evaluate_statute(client, args.search_size)
    natural = evaluate_natural(client, args.search_size)
    compare = evaluate_compare(client, natural["base_case_ids"][:10], args.compare_limit)
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "statute": statute,
        "natural": {key: value for key, value in natural.items() if key != "base_case_ids"},
        "compare": compare,
        "db_snapshot": db_quality_snapshot(),
    }

    json_path = ROOT / args.json_output
    md_path = ROOT / args.markdown_output
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({
        "json_output": str(json_path),
        "markdown_output": str(md_path),
        "summary": {
            "statute_precision_at_10": report["statute"]["metric"]["precision_at_10"],
            "natural_avg_top5_relevant_count": report["natural"]["metric"]["avg_top5_relevant_count"],
            "compare_avg_material_fact_match": report["compare"]["metric"]["avg_material_fact_match"],
            "needs_review_rate": report["db_snapshot"]["needs_review_rate"],
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
