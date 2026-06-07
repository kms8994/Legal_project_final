from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from pipelines.common.articles import LAW_ALIASES, make_normalized_ref, normalize_law_name


DEFAULT_LAW_ALIASES = {
    **LAW_ALIASES,
}

DEFAULT_KNOWN_ARTICLES = {
    # 민사
    "민법_제393조",
    "민법_제396조",
    "민법_제750조",
    "민법_제751조",
    "민법_제763조",
    "자동차손해배상 보장법_제3조",
    # 형사 — 주요 조문
    "형법_제250조",   # 살인
    "형법_제257조",   # 상해
    "형법_제258조의2", # 특수상해
    "형법_제260조",   # 폭행
    "형법_제261조",   # 특수폭행
    "형법_제276조",   # 체포·감금
    "형법_제297조",   # 강간
    "형법_제298조",   # 강제추행
    "형법_제329조",   # 절도
    "형법_제330조",   # 야간주거침입절도
    "형법_제333조",   # 강도
    "형법_제347조",   # 사기
    "형법_제355조",   # 횡령·배임
    "형법_제356조",   # 업무상횡령·배임
    "형법_제366조",   # 재물손괴
    "형법_제314조",   # 업무방해
    "형사소송법_제307조",  # 증거재판주의
    "형사소송법_제308조의2", # 위법수집증거배제
    "도로교통법_제44조",   # 음주운전
    "도로교통법_제148조의2", # 음주운전 처벌
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

CRIMINAL_KEYWORDS = [
    "공소사실",
    "범죄사실",
    "피고인",
    "검사",
    "공소",
    "징역",
    "벌금",
    "집행유예",
    "무죄",
    "유죄",
    "선고",
    "양형",
    "구속",
    "체포",
    "기소",
    "형사",
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
    criminal_keywords = extract_criminal_keywords(text)
    if not cited_articles:
        cited_articles = infer_cited_articles(text, keywords, known)
    outcome = extract_outcome(text, is_criminal=bool(criminal_keywords))
    legal_domain = infer_legal_domain(text, keywords, criminal_keywords)
    facets = {
        "legal_domain": legal_domain,
        "case_type": case_type,
        "court_level": court_level,
        "harm_type": infer_harm_type(text),
    }
    evidence_spans = {
        "cited_articles": [article["evidence"] for article in cited_articles],
        "outcome": outcome.get("evidence"),
        "keywords": evidence_for_keywords(text, keywords + criminal_keywords),
    }
    confidence_score = score_confidence(cited_articles, keywords + criminal_keywords, outcome)
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
        r"(?:(민법|민\s*법"
        r"|자동차손해배상\s*보장법|자동차손해배상보장법|자동차손해배상법|자배법|자동차손배법"
        r"|형법|형\s*법"
        r"|형사소송법|형소법"
        r"|도로교통법"
        r"|특정범죄\s*가중처벌\s*등에\s*관한\s*법률|특가법"
        r"|특정경제범죄\s*가중처벌\s*등에\s*관한\s*법률|특경법"
        r"|성폭력범죄의\s*처벌\s*등에\s*관한\s*특례법|성폭력처벌법"
        r"|마약류\s*관리에\s*관한\s*법률|마약류관리법"
        r"|아동·청소년의\s*성보호에\s*관한\s*법률|아청법"
        r")\s*)?"
        r"(?:제\s*)?(\d+)\s*조?(?:\s*의\s*(\d+))?"
    )
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    last_law_name = "민법"
    for match in pattern.finditer(text):
        alias, article_no, branch_no = match.groups()
        if alias:
            last_law_name = law_aliases.get(
                re.sub(r"\s+", " ", alias.strip()),
                normalize_law_name(alias),
            )
        law_name = normalize_law_name(last_law_name)
        normalized_ref = make_normalized_ref(
            law_name,
            int(article_no),
            int(branch_no) if branch_no else None,
        )
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


def extract_criminal_keywords(text: str) -> list[str]:
    return [keyword for keyword in CRIMINAL_KEYWORDS if keyword in text]


def infer_legal_domain(text: str, keywords: list[str], criminal_keywords: list[str]) -> str:
    if len(criminal_keywords) >= 2 or any(k in text for k in ["공소사실", "범죄사실", "피고인", "징역", "벌금"]):
        return "형사"
    if is_damages_case(text, keywords):
        return "손해배상"
    return "unknown"


def infer_cited_articles(
    text: str,
    keywords: list[str],
    known_articles: set[str],
) -> list[dict[str, Any]]:
    if "민법_제750조" not in known_articles:
        return []
    strong_terms = ["불법행위", "손해배상", "교통사고", "과실상계", "위자료"]
    if not any(term in text for term in strong_terms) and len(keywords) < 2:
        return []
    evidence_term = next((term for term in strong_terms if term in text), None)
    if not evidence_term:
        evidence_term = keywords[0] if keywords else "손해배상"
    index = text.find(evidence_term)
    if index < 0:
        index = 0
    return [
        {
            "normalized_ref": "민법_제750조",
            "law_name": "민법",
            "article_no": 750,
            "article_branch_no": None,
            "inferred": True,
            "inference_reason": "damages_keyword_without_explicit_citation",
            "evidence": {
                "char_start": index,
                "char_end": index + len(evidence_term),
                "text": evidence_term,
            },
        }
    ]


def extract_outcome(text: str, is_criminal: bool = False) -> dict[str, Any]:
    if is_criminal:
        return _extract_criminal_outcome(text)
    return _extract_civil_outcome(text)


def _extract_civil_outcome(text: str) -> dict[str, Any]:
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
                "confidence": 0.65,
                "evidence": {"char_start": index, "char_end": index + len(keyword), "text": keyword},
            }
    return {"disposition": "unknown", "direction": "unknown", "confidence": 0.2, "evidence": None}


def _extract_criminal_outcome(text: str) -> dict[str, Any]:
    """형사 판결 결과 추출: 선고형, 무죄/유죄, 집행유예 여부"""
    # 무죄 판단 우선
    if "무죄" in text:
        idx = text.find("무죄")
        return {
            "disposition": "무죄",
            "direction": "피고인 유리",
            "sentence_type": "무죄",
            "suspended": False,
            "confidence": 0.75,
            "evidence": {"char_start": idx, "char_end": idx + 2, "text": "무죄"},
        }
    # 징역/금고 + 집행유예
    import re as _re
    sentence_match = _re.search(r"(징역|금고)\s*([\d]+)\s*(년|개월)", text)
    suspended = "집행유예" in text
    if sentence_match:
        term = sentence_match.group(0)
        idx = sentence_match.start()
        return {
            "disposition": "유죄",
            "direction": "피고인 불리",
            "sentence_type": "징역" if "징역" in term else "금고",
            "sentence_term": term,
            "suspended": suspended,
            "confidence": 0.75,
            "evidence": {"char_start": idx, "char_end": idx + len(term), "text": term},
        }
    # 벌금
    fine_match = _re.search(r"벌금\s*([\d,]+)\s*원", text)
    if fine_match:
        idx = fine_match.start()
        return {
            "disposition": "유죄",
            "direction": "피고인 불리",
            "sentence_type": "벌금",
            "sentence_term": fine_match.group(0),
            "suspended": False,
            "confidence": 0.7,
            "evidence": {"char_start": idx, "char_end": fine_match.end(), "text": fine_match.group(0)},
        }
    # 상고기각/파기환송
    for keyword, disposition, direction in [
        ("파기환송", "파기환송", "원심 파기"),
        ("상고기각", "상고기각", "원심 유지"),
        ("항소기각", "항소기각", "원심 유지"),
    ]:
        idx = text.find(keyword)
        if idx >= 0:
            return {
                "disposition": disposition,
                "direction": direction,
                "confidence": 0.65,
                "evidence": {"char_start": idx, "char_end": idx + len(keyword), "text": keyword},
            }
    return {"disposition": "unknown", "direction": "unknown", "confidence": 0.2, "evidence": None}


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
        if all(article.get("inferred") for article in cited_articles):
            score += 0.15
        else:
            score += 0.3
    if keywords:
        score += min(len(keywords) * 0.05, 0.2)
    if outcome.get("disposition") != "unknown":
        score += 0.2
    return min(score, 0.95)


def without_evidence(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "evidence"}
