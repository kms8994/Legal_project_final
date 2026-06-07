from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GeminiGenerationError(RuntimeError):
    pass


def generate_case_summary(
    *,
    api_key: str,
    model: str,
    case_name: str,
    case_no: str,
    structured_fields: dict[str, Any],
    evidence_links: list[dict[str, str]],
    timeout_seconds: int = 25,
) -> dict[str, str]:
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": _prompt(
                            case_name=case_name,
                            case_no=case_no,
                            structured_fields=structured_fields,
                            evidence_links=evidence_links,
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GeminiGenerationError(f"Gemini HTTP {exc.code}: {_truncate(detail)}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GeminiGenerationError(f"Gemini request failed: {_truncate(str(exc))}") from exc

    text = _extract_text(body)
    return _parse_summary_json(text)


def _prompt(
    *,
    case_name: str,
    case_no: str,
    structured_fields: dict[str, Any],
    evidence_links: list[dict[str, str]],
) -> str:
    return (
        "You are generating a grounded Korean case summary for a legal research UI.\n"
        "Use only the structured fields and evidence paragraphs below.\n"
        "Do not invent facts, statutes, amounts, dates, ratios, or legal conclusions.\n"
        "If evidence is insufficient, say that the field is not clear from the provided evidence.\n"
        "Return only JSON with string keys: facts, issue, reasoning, outcome.\n\n"
        f"Case name: {case_name}\n"
        f"Case number: {case_no}\n"
        f"Structured fields JSON: {json.dumps(structured_fields, ensure_ascii=False)}\n"
        f"Evidence JSON: {json.dumps(evidence_links, ensure_ascii=False)}"
    )


def _extract_text(body: dict[str, Any]) -> str:
    try:
        parts = body["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiGenerationError("Gemini response did not include text parts.") from exc
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise GeminiGenerationError("Gemini response text was empty.")
    return text


def _parse_summary_json(text: str) -> dict[str, str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiGenerationError("Gemini response was not valid JSON.") from exc

    result: dict[str, str] = {}
    for key in ("facts", "issue", "reasoning", "outcome"):
        value = parsed.get(key)
        result[key] = value.strip() if isinstance(value, str) and value.strip() else ""
    if not any(result.values()):
        raise GeminiGenerationError("Gemini summary JSON did not include usable text.")
    return result


def generate_display_summaries(
    *,
    api_key: str,
    model: str,
    case_no: str,
    case_name: str,
    facts: str | None,
    legal_issue: str | None,
    court_reasoning: str | None,
    conclusion: str | None,
    outcome: dict[str, Any],
    timeout_seconds: int = 25,
) -> dict[str, Any]:
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": _display_summary_prompt(
                            case_no=case_no,
                            case_name=case_name,
                            facts=facts,
                            legal_issue=legal_issue,
                            court_reasoning=court_reasoning,
                            conclusion=conclusion,
                            outcome=outcome,
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GeminiGenerationError(f"Gemini HTTP {exc.code}: {_truncate(detail)}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GeminiGenerationError(f"Gemini request failed: {_truncate(str(exc))}") from exc

    text_body = _extract_text(body)
    return _parse_display_summary_json(text_body)


def _is_criminal_case(outcome: dict[str, Any], case_name: str) -> bool:
    criminal_signals = ["징역", "벌금", "무죄", "집행유예", "유죄", "형사"]
    return (
        any(s in case_name for s in criminal_signals)
        or outcome.get("sentence_type") is not None
        or outcome.get("legal_domain") == "형사"
    )


def _display_summary_prompt(
    *,
    case_no: str,
    case_name: str,
    facts: str | None,
    legal_issue: str | None,
    court_reasoning: str | None,
    conclusion: str | None,
    outcome: dict[str, Any],
) -> str:
    def _clip(s: str | None, n: int = 800) -> str:
        if not s:
            return "(없음)"
        s = s.strip()
        return s[:n] + "..." if len(s) > n else s

    is_criminal = _is_criminal_case(outcome, case_name)

    if is_criminal:
        facts_hint = "누가 어떤 범죄를 저질렀는지, 피해 상황 중심으로."
        judgment_hint = "선고형(징역 몇 년, 벌금 얼마, 집행유예 여부 등)을 포함하여 결론 설명."
    else:
        facts_hint = "누가 누구에게 무엇을 청구했는지 중심으로."
        judgment_hint = "기각/인용/파기환송 등 결론과 배상액이 있으면 포함."

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


def _parse_display_summary_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiGenerationError("Gemini display summary response was not valid JSON.") from exc

    required = ("one_line", "facts_summary", "judgment_summary")
    if not any(parsed.get(k) for k in required):
        raise GeminiGenerationError("Gemini display summary JSON missing required fields.")
    return parsed


def generate_compare_analysis(
    *,
    api_key: str,
    model: str,
    base_case_no: str,
    compare_case_no: str,
    structured_fields: dict[str, Any],
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": _compare_prompt(
                            base_case_no=base_case_no,
                            compare_case_no=compare_case_no,
                            structured_fields=structured_fields,
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GeminiGenerationError(f"Gemini HTTP {exc.code}: {_truncate(detail)}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GeminiGenerationError(f"Gemini request failed: {_truncate(str(exc))}") from exc

    text = _extract_text(body)
    return _parse_compare_json(text)


def _compare_prompt(
    *,
    base_case_no: str,
    compare_case_no: str,
    structured_fields: dict[str, Any],
) -> str:
    return (
        "당신은 한국 법률 판례 비교 분석 전문가입니다.\n"
        "아래 두 판례의 구조화된 데이터를 바탕으로 비교 분석을 한국어로 생성하세요.\n"
        "데이터에 없는 사실, 법령, 금액, 날짜, 비율, 법적 결론을 절대 지어내지 마세요.\n"
        "데이터가 부족하면 '해당 정보가 제공된 데이터에서 확인되지 않습니다'라고 작성하세요.\n\n"
        "반드시 다음 JSON 형식으로만 응답하세요:\n"
        "{\n"
        '  "result_difference": "두 판례의 결론 차이를 자연스러운 한국어 2-3문장으로",\n'
        '  "common_points": [\n'
        '    {"text": "공통점을 한국어 한 문장으로"},\n'
        "    ...\n"
        "  ],\n"
        '  "material_differences": [\n'
        '    {"factor": "쟁점 항목 이름(한국어)", "base": "기준 판례 내용", "compare": "비교 판례 내용", "meaning": "법적 의미 한 문장"},\n'
        "    ...\n"
        "  ],\n"
        '  "turning_points": [\n'
        '    {"title": "판단 갈림 지점 제목(한국어)", "explanation": "설명 1-2문장"},\n'
        "    ...\n"
        "  ]\n"
        "}\n\n"
        f"기준 판례 번호: {base_case_no}\n"
        f"비교 판례 번호: {compare_case_no}\n"
        f"구조화 데이터: {json.dumps(structured_fields, ensure_ascii=False)}"
    )


def _parse_compare_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise GeminiGenerationError("Gemini compare response was not valid JSON.") from exc

    required = ("result_difference", "common_points", "material_differences", "turning_points")
    if not any(parsed.get(k) for k in required):
        raise GeminiGenerationError("Gemini compare JSON did not include usable content.")
    return parsed


def _truncate(value: str, limit: int = 300) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
