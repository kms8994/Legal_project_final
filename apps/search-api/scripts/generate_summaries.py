"""
case_summaries 일괄 생성 스크립트.

사용법:
    python scripts/generate_summaries.py [--limit N] [--overwrite]

--limit N    : 최대 N개만 처리 (기본: 전체)
--overwrite  : 이미 요약이 있는 판례도 재생성
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.services.gemini import GeminiGenerationError, generate_display_summaries


DISPOSITION_KEYWORDS = {
    "파기환송": "파기환송",
    "파기자판": "파기자판",
    "일부 인용": "일부인용",
    "일부인용": "일부인용",
    "일부승": "일부인용",
    "인용": "인용",
    "승소": "인용",
    "기각": "기각",
    "패소": "기각",
    "각하": "각하",
}


def _extract_disposition(conclusion: str | None, outcome: dict) -> str | None:
    """conclusion 텍스트와 outcome 구조에서 disposition enum 추출."""
    raw = outcome.get("disposition") or outcome.get("outcome_disposition") or ""
    if raw:
        for k, v in DISPOSITION_KEYWORDS.items():
            if k in str(raw):
                return v

    text_src = (conclusion or "") + " " + str(outcome.get("direction", ""))
    for k, v in DISPOSITION_KEYWORDS.items():
        if k in text_src:
            return v
    return None


def _input_hash(case_no: str, facts: str | None, conclusion: str | None, outcome: dict) -> str:
    payload = json.dumps(
        {"case_no": case_no, "facts": facts, "conclusion": conclusion, "outcome": outcome},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def fetch_cases(conn, overwrite: bool, limit: int | None) -> list[dict]:
    """요약이 없는(또는 전체) 판례 목록 조회."""
    limit_clause = f"limit {limit}" if limit else ""
    if overwrite:
        where_clause = ""
    else:
        where_clause = "and case_summaries.id is null"

    rows = conn.execute(
        text(
            f"""
            select
              cases.id::text as case_id,
              cases.case_no,
              cases.case_name,
              cs.facts,
              cs.legal_issue,
              cs.court_reasoning,
              cs.conclusion,
              cs.material_facts,
              cs.outcome
            from cases
            join (
              select distinct on (case_id)
                case_id, facts, legal_issue, court_reasoning,
                conclusion, material_facts, outcome
              from case_structures
              order by case_id,
                (material_facts is not null and material_facts <> '{{}}'::jsonb) desc,
                (nullif(btrim(coalesce(facts, '')), '') is not null) desc,
                processed_at desc
            ) cs on cs.case_id = cases.id
            left join case_summaries on case_summaries.case_id = cases.id
            where cases.is_deleted = false
              {where_clause}
            order by cases.decision_date desc nulls last
            {limit_clause}
            """
        )
    ).mappings().all()

    return [dict(r) for r in rows]


def upsert_summary(conn, case_id: str, summary: dict, input_hash: str) -> None:
    conn.execute(
        text(
            """
            insert into case_summaries
              (case_id, one_line, facts_summary, issue_summary,
               reasoning_summary, judgment_summary, disposition,
               generated_by, input_hash, updated_at)
            values
              (:case_id, :one_line, :facts_summary, :issue_summary,
               :reasoning_summary, :judgment_summary, :disposition,
               :generated_by, :input_hash, now())
            on conflict (case_id) do update set
              one_line          = excluded.one_line,
              facts_summary     = excluded.facts_summary,
              issue_summary     = excluded.issue_summary,
              reasoning_summary = excluded.reasoning_summary,
              judgment_summary  = excluded.judgment_summary,
              disposition       = excluded.disposition,
              generated_by      = excluded.generated_by,
              input_hash        = excluded.input_hash,
              updated_at        = now()
            """
        ),
        {
            "case_id": case_id,
            "one_line": summary.get("one_line", ""),
            "facts_summary": summary.get("facts_summary", ""),
            "issue_summary": summary.get("issue_summary"),
            "reasoning_summary": summary.get("reasoning_summary"),
            "judgment_summary": summary.get("judgment_summary", ""),
            "disposition": summary.get("disposition"),
            "generated_by": summary.get("generated_by", settings.gemini_model),
            "input_hash": input_hash,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not settings.gemini_api_key:
        print("GEMINI_API_KEY가 설정되지 않았습니다.")
        sys.exit(1)

    # 케이스 목록은 짧은 연결로만 조회
    with engine.connect() as conn:
        cases = fetch_cases(conn, overwrite=args.overwrite, limit=args.limit)
    print(f"처리 대상: {len(cases)}건")

    ok = 0
    fail = 0
    skip = 0

    for i, case in enumerate(cases, 1):
        case_id = case["case_id"]
        case_no = case["case_no"]
        outcome = case["outcome"] if isinstance(case["outcome"], dict) else {}

        h = _input_hash(case_no, case["facts"], case["conclusion"], outcome)

        print(f"[{i}/{len(cases)}] {case_no} ...", end=" ", flush=True)
        try:
            generated = generate_display_summaries(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                case_no=case_no,
                case_name=case["case_name"],
                facts=case["facts"],
                legal_issue=case["legal_issue"],
                court_reasoning=case["court_reasoning"],
                conclusion=case["conclusion"],
                outcome=outcome,
            )
            generated["disposition"] = _extract_disposition(case["conclusion"], outcome)
            generated["generated_by"] = settings.gemini_model

            # DB 작업마다 새 연결 사용 → Supabase idle timeout 방지
            with engine.begin() as conn:
                existing_hash = conn.execute(
                    text("select input_hash from case_summaries where case_id = :cid"),
                    {"cid": case_id},
                ).scalar()
                if existing_hash == h and not args.overwrite:
                    skip += 1
                    print("SKIP")
                    time.sleep(4)
                    continue
                upsert_summary(conn, case_id, generated, h)
            ok += 1
            print("OK")
        except GeminiGenerationError as exc:
            fail += 1
            print(f"FAIL: {exc}")
        except Exception as exc:
            fail += 1
            print(f"ERROR: {exc}")

        # Gemini free tier: 분당 15 RPM 제한 대응
        time.sleep(4)

    print(f"\n완료: 성공 {ok} / 실패 {fail} / 건너뜀 {skip}")


if __name__ == "__main__":
    main()
