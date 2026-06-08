"""Backfill missing/low-quality case_summaries using Gemini 2.5 Flash."""

import hashlib
import json
import os
import sys
import time

import psycopg2

# ── Gemini helpers (inline to keep script standalone) ─────────────────
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:finalprojectLegal5325@db.lkpsrzbuvrgkopqatvbb.supabase.co:5432/postgres",
)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBL6pobaY7qCJtV6s7c0vIh-EVorX4_DSo")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

RATE_LIMIT_DELAY = 4  # seconds between requests (free tier: ~15 RPM)


def _clip(s: str | None, n: int = 800) -> str:
    if not s:
        return "(없음)"
    s = s.strip()
    return s[:n] + "..." if len(s) > n else s


def _is_criminal(outcome: dict, case_name: str) -> bool:
    signals = ["징역", "벌금", "무죄", "집행유예", "유죄", "형사"]
    return (
        any(s in case_name for s in signals)
        or outcome.get("sentence_type") is not None
        or outcome.get("legal_domain") == "형사"
    )


def build_prompt(case_no, case_name, facts, legal_issue, court_reasoning, conclusion, outcome):
    is_crim = _is_criminal(outcome, case_name)
    facts_hint = "누가 어떤 범죄를 저질렀는지, 피해 상황 중심으로." if is_crim else "누가 누구에게 무엇을 청구했는지 중심으로."
    judgment_hint = (
        "선고형(징역 몇 년, 벌금 얼마, 집행유예 여부 등)을 포함하여 결론 설명."
        if is_crim
        else "기각/인용/파기환송 등 결론과 배상액이 있으면 포함."
    )
    return (
        "당신은 한국 법원 판결문을 읽고 일반 사용자가 이해하기 쉽게 요약하는 전문가입니다.\n"
        "아래 판결문 데이터를 바탕으로 각 항목을 자연스러운 한국어로 요약하세요.\n"
        "데이터에 없는 사실, 수치, 날짜를 절대 지어내지 마세요.\n"
        "데이터가 부족하면 '해당 정보를 확인할 수 없습니다'라고 쓰세요.\n\n"
        "반드시 다음 JSON 형식으로만 응답하세요:\n"
        "{\n"
        '  "one_line": "이 사건을 한 문장(40자 이내)으로 요약",\n'
        f'  "facts_summary": "사실관계를 2-3문장으로 요약. {facts_hint}",\n'
        '  "issue_summary": "법적 쟁점을 1-2문장으로 요약",\n'
        '  "reasoning_summary": "법원의 판단 근거를 2-3문장으로 요약. 핵심 법리나 인정된 사실 중심으로.",\n'
        f'  "judgment_summary": "판결 결과를 1-2문장으로 자연어로 설명. {judgment_hint}"\n'
        "}\n\n"
        f"사건번호: {case_no}\n"
        f"사건명: {case_name}\n"
        f"사실관계: {_clip(facts)}\n"
        f"법적 쟁점: {_clip(legal_issue, 400)}\n"
        f"법원의 판단: {_clip(court_reasoning)}\n"
        f"결론: {_clip(conclusion, 400)}\n"
        f"판결 구조화 데이터: {json.dumps(outcome, ensure_ascii=False)}"
    )


def call_gemini(prompt: str) -> dict:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    req = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_KEY},
        method="POST",
    )
    with urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = body["candidates"][0]["content"]["parts"][0]["text"]
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Find cases needing regeneration
    cur.execute("""
        SELECT DISTINCT ON (c.id)
               c.id, c.case_no, c.case_name,
               st.facts, st.legal_issue, st.court_reasoning, st.conclusion, st.outcome
        FROM cases c
        JOIN case_structures st ON c.id = st.case_id
        LEFT JOIN case_summaries cs ON c.id = cs.case_id
        WHERE cs.case_id IS NULL
           OR cs.reasoning_summary IS NULL
           OR LENGTH(cs.reasoning_summary) < 30
           OR cs.reasoning_summary LIKE '%확인할 수 없%'
        ORDER BY c.id, st.confidence_score DESC NULLS LAST
    """)
    rows = cur.fetchall()
    total = len(rows)
    print(f"=== {total}건 재생성 필요 ===\n")

    success = 0
    failed = 0

    for i, (case_id, case_no, case_name, facts, legal_issue, court_reasoning, conclusion, outcome_raw) in enumerate(rows):
        outcome = outcome_raw if isinstance(outcome_raw, dict) else (json.loads(outcome_raw) if outcome_raw else {})

        print(f"[{i+1}/{total}] {case_no} ... ", end="", flush=True)

        try:
            prompt = build_prompt(case_no, case_name, facts, legal_issue, court_reasoning, conclusion, outcome)
            result = call_gemini(prompt)

            one_line = result.get("one_line", "")
            facts_summary = result.get("facts_summary", "")
            issue_summary = result.get("issue_summary", "")
            reasoning_summary = result.get("reasoning_summary", "")
            judgment_summary = result.get("judgment_summary", "")

            # Compute input_hash from source fields
            hash_src = f"{facts}{legal_issue}{court_reasoning}{conclusion}"
            input_hash = hashlib.sha256(hash_src.encode("utf-8")).hexdigest()[:16]

            # Upsert into case_summaries
            cur.execute("""
                INSERT INTO case_summaries (case_id, one_line, facts_summary, issue_summary, reasoning_summary, judgment_summary, generated_by, input_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (case_id)
                DO UPDATE SET
                    one_line = EXCLUDED.one_line,
                    facts_summary = EXCLUDED.facts_summary,
                    issue_summary = EXCLUDED.issue_summary,
                    reasoning_summary = EXCLUDED.reasoning_summary,
                    judgment_summary = EXCLUDED.judgment_summary,
                    generated_by = EXCLUDED.generated_by,
                    input_hash = EXCLUDED.input_hash
            """, (case_id, one_line, facts_summary, issue_summary, reasoning_summary, judgment_summary, 'gemini-2.5-flash-backfill', input_hash))
            conn.commit()
            success += 1
            print(f"OK ({one_line[:30]}...)")

        except Exception as e:
            failed += 1
            print(f"FAIL: {e}")
            conn.rollback()

        # Rate limit
        if i < total - 1:
            time.sleep(RATE_LIMIT_DELAY)

    cur.close()
    conn.close()
    print(f"\n=== 완료: 성공 {success}, 실패 {failed} / 전체 {total} ===")


if __name__ == "__main__":
    main()
