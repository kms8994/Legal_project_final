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


def _truncate(value: str, limit: int = 300) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
