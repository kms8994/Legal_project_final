from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


DEFAULT_LAW_ALIASES = {
    "민법": "민법",
    "자동차손해배상 보장법": "자동차손해배상 보장법",
    "자동차손해배상보장법": "자동차손해배상 보장법",
    "자배법": "자동차손해배상 보장법",
    "자동차손배법": "자동차손해배상 보장법",
}

DEFAULT_KNOWN_ARTICLES = {
    "민법_제393조",
    "민법_제396조",
    "민법_제750조",
    "민법_제751조",
    "민법_제763조",
    "자동차손해배상 보장법_제3조",
}

DAMAGES_KEYWORDS = [
    "손해배상",
    "불법행위",
    "위자료",
    "과실상계",
    "인과관계",
    "치료비",
    "일실수입",
    "자동차",
    "교통사고",
]


@dataclass(frozen=True)
class ExtractedCase:
    cited_articles: list[dict[str, Any]]
    facets: dict[str, Any]
    outcome: dict[str, Any]
    evidence_spans: dict[str, Any]
    keywords: list[str]
    confidence_score: float
    structure_hash: str


def extract_case_features(
    text: str,
    case_type: str | None = None,
    court_level: str | None = None,
    law_aliases: dict[str, str] | None = None,
    known_articles: set[str] | None = None,
) -> ExtractedCase:
    aliases = law_aliases or DEFAULT_LAW_ALIASES
    known = known_articles or DEFAULT_KNOWN_ARTICLES
    cited_articles = extract_cited_articles(text, aliases, known)
    keywords = extract_keywords(text)
    outcome = extract_outcome(text)
    facets = {
        "legal_domain": "손해배상" if is_damages_case(text, keywords) else "unknown",
        "case_type": case_type,
        "court_level": court_level,
        "harm_type": infer_harm_type(text),
    }
    evidence_spans = {
        "cited_articles": [article["evidence"] for article in cited_articles],
        "outcome": outcome.get("evidence"),
        "keywords": evidence_for_keywords(text, keywords),
    }
    confidence_score = score_confidence(cited_articles, keywords, outcome)
    hash_payload = repr((cited_articles, facets, outcome, keywords))
    return ExtractedCase(
        cited_articles=[without_evidence(article) for article in cited_articles],
        facets=facets,
        outcome=without_evidence(outcome),
        evidence_spans=evidence_spans,
        keywords=keywords,
        confidence_score=confidence_score,
        structure_hash=hashlib.sha256(hash_payload.encode("utf-8")).hexdigest(),
    )


def extract_cited_articles(
    text: str,
    law_aliases: dict[str, str],
    known_articles: set[str],
) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?:(민법|자동차손해배상\s*보장법|자동차손해배상보장법|자배법|자동차손배법)\s*)?"
        r"제\s*(\d+)\s*조(?:의\s*(\d+))?"
    )
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    last_law_name = "민법"
    for match in pattern.finditer(text):
        alias, article_no, branch_no = match.groups()
        if alias:
            last_law_name = law_aliases.get(re.sub(r"\s+", " ", alias.strip()), alias.strip())
        law_name = last_law_name
        branch = f"의{int(branch_no)}" if branch_no else ""
        normalized_ref = f"{law_name}_제{int(article_no)}조{branch}"
        if normalized_ref not in known_articles and alias is None:
            continue
        if normalized_ref in seen:
            continue
        seen.add(normalized_ref)
        found.append(
            {
                "normalized_ref": normalized_ref,
                "law_name": law_name,
                "article_no": int(article_no),
                "article_branch_no": int(branch_no) if branch_no else None,
                "evidence": {
                    "char_start": match.start(),
                    "char_end": match.end(),
                    "text": match.group(0),
                },
            }
        )
    return found


def extract_keywords(text: str) -> list[str]:
    return [keyword for keyword in DAMAGES_KEYWORDS if keyword in text]


def extract_outcome(text: str) -> dict[str, Any]:
    candidates = [
        ("파기", "파기", "원심 파기"),
        ("일부 인용", "일부 인용", "원고 일부 유리"),
        ("인용한다", "인용", "원고 유리"),
        ("기각한다", "기각", "원고 불리"),
        ("각하", "각하", "원고 불리"),
    ]
    for keyword, disposition, direction in candidates:
        index = text.find(keyword)
        if index >= 0:
            return {
                "disposition": disposition,
                "direction": direction,
                "key_factor": keyword,
                "confidence": 0.65,
                "evidence": {
                    "char_start": index,
                    "char_end": index + len(keyword),
                    "text": keyword,
                },
            }
    return {
        "disposition": "unknown",
        "direction": "unknown",
        "confidence": 0.2,
        "evidence": None,
    }


def evidence_for_keywords(text: str, keywords: list[str]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for keyword in keywords:
        index = text.find(keyword)
        if index >= 0:
            spans.append({"keyword": keyword, "char_start": index, "char_end": index + len(keyword)})
    return spans


def infer_harm_type(text: str) -> str:
    if any(keyword in text for keyword in ["상해", "치료비", "일실수입", "사망", "부상"]):
        return "신체"
    if any(keyword in text for keyword in ["명예", "정신상", "위자료"]):
        return "정신"
    if any(keyword in text for keyword in ["재산", "부동산", "차량", "수리비"]):
        return "재산"
    return "unknown"


def is_damages_case(text: str, keywords: list[str]) -> bool:
    return "손해배상" in text or "불법행위" in text or len(keywords) >= 2


def score_confidence(
    cited_articles: list[dict[str, Any]],
    keywords: list[str],
    outcome: dict[str, Any],
) -> float:
    score = 0.25
    if cited_articles:
        score += 0.3
    if keywords:
        score += min(len(keywords) * 0.05, 0.2)
    if outcome.get("disposition") != "unknown":
        score += 0.2
    return min(score, 0.95)


def without_evidence(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "evidence"}
