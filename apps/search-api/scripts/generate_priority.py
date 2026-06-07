"""민법 제750조 검색 결과 상위 판례 우선 요약 생성."""
from __future__ import annotations
import json, sys, time, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine
from app.services.gemini import GeminiGenerationError, generate_display_summaries

DISPOSITION_KEYWORDS = {
    "파기환송": "파기환송", "파기자판": "파기자판",
    "일부 인용": "일부인용", "일부인용": "일부인용",
    "인용": "인용", "기각": "기각", "각하": "각하",
}

def _disposition(conclusion, outcome):
    raw = str(outcome.get("disposition") or outcome.get("outcome_disposition") or "")
    for k, v in DISPOSITION_KEYWORDS.items():
        if k in raw: return v
    src = (conclusion or "") + " " + str(outcome.get("direction", ""))
    for k, v in DISPOSITION_KEYWORDS.items():
        if k in src: return v
    return None

def _hash(case_no, facts, conclusion, outcome):
    p = json.dumps({"case_no": case_no, "facts": facts, "conclusion": conclusion, "outcome": outcome}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(p.encode()).hexdigest()[:16]

# 모든 사용자가 검색할 만한 주요 조문들의 결과 판례 수집
PRIORITY_REFS = [
    {"normalized_ref": "민법 제750조"},
    {"normalized_ref": "민법 제396조"},
    {"normalized_ref": "민법 제35조"},
    {"normalized_ref": "자동차손해배상 보장법 제3조"},
]

with engine.connect() as conn:
    seen = set()
    cases = []
    for ref in PRIORITY_REFS:
        payload = json.dumps([ref], ensure_ascii=False)
        rows = conn.execute(text("""
            select cases.id::text as case_id, cases.case_no, cases.case_name,
                   cs.facts, cs.legal_issue, cs.court_reasoning, cs.conclusion, cs.material_facts, cs.outcome
            from (select distinct on (case_id) case_id, facts, legal_issue, court_reasoning, conclusion,
                   material_facts, outcome, cited_articles from case_structures
                   order by case_id, (material_facts is not null and material_facts <> '{}'::jsonb) desc,
                   processed_at desc) cs
            join cases on cases.id = cs.case_id
            left join case_summaries on case_summaries.case_id = cases.id
            where cases.is_deleted = false
              and cs.cited_articles @> cast(:p as jsonb)
              and case_summaries.id is null
            order by cases.decision_date desc nulls last
            limit 15
        """), {"p": payload}).mappings().all()
        for r in rows:
            if r["case_id"] not in seen:
                seen.add(r["case_id"])
                cases.append(dict(r))

    print(f"우선 처리 대상: {len(cases)}건", flush=True)
    ok = fail = 0
    for i, case in enumerate(cases, 1):
        outcome = case["outcome"] if isinstance(case["outcome"], dict) else {}
        h = _hash(case["case_no"], case["facts"], case["conclusion"], outcome)
        print(f"[{i}/{len(cases)}] {case['case_no']} ...", end=" ", flush=True)
        try:
            gen = generate_display_summaries(
                api_key=settings.gemini_api_key, model=settings.gemini_model,
                case_no=case["case_no"], case_name=case["case_name"],
                facts=case["facts"], legal_issue=case["legal_issue"],
                court_reasoning=case["court_reasoning"], conclusion=case["conclusion"],
                outcome=outcome,
            )
            gen["disposition"] = _disposition(case["conclusion"], outcome)
            gen["generated_by"] = settings.gemini_model
            conn.execute(text("""
                insert into case_summaries (case_id,one_line,facts_summary,issue_summary,reasoning_summary,judgment_summary,disposition,generated_by,input_hash,updated_at)
                values (:case_id,:one_line,:facts_summary,:issue_summary,:reasoning_summary,:judgment_summary,:disposition,:generated_by,:input_hash,now())
                on conflict (case_id) do update set one_line=excluded.one_line, facts_summary=excluded.facts_summary,
                  issue_summary=excluded.issue_summary, reasoning_summary=excluded.reasoning_summary,
                  judgment_summary=excluded.judgment_summary, disposition=excluded.disposition,
                  generated_by=excluded.generated_by, input_hash=excluded.input_hash, updated_at=now()
            """), {
                "case_id": case["case_id"], "one_line": gen.get("one_line",""),
                "facts_summary": gen.get("facts_summary",""), "issue_summary": gen.get("issue_summary"),
                "reasoning_summary": gen.get("reasoning_summary"), "judgment_summary": gen.get("judgment_summary",""),
                "disposition": gen.get("disposition"), "generated_by": gen.get("generated_by",""),
                "input_hash": h,
            })
            conn.commit()
            ok += 1
            print("OK", flush=True)
        except GeminiGenerationError as e:
            fail += 1
            print(f"FAIL: {e}", flush=True)
        time.sleep(4)
    print(f"\n완료: 성공 {ok} / 실패 {fail}")
