from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from pipelines.common.extract import extract_case_features
from pipelines.common.text import Paragraph, split_case_text


@dataclass(frozen=True)
class StructuredCase:
    cited_articles: list[dict[str, Any]]
    facts: str | None
    legal_issue: str | None
    court_reasoning: str | None
    conclusion: str | None
    material_facts: dict[str, Any]
    aggravating_factors: list[str]
    mitigating_factors: list[str]
    key_disputed_facts: list[str]
    outcome: dict[str, Any]
    facets: dict[str, Any]
    evidence_spans: dict[str, Any]
    confidence_score: float
    review_status: str
    structure_hash: str


def structure_case_text(
    text: str,
    case_type: str | None = None,
    court_level: str | None = None,
    case_name: str | None = None,
    law_aliases: dict[str, str] | None = None,
    known_articles: set[str] | None = None,
) -> StructuredCase:
    paragraphs = split_case_text(text)
    extracted = extract_case_features(
        text,
        case_type=case_type,
        court_level=court_level,
        law_aliases=law_aliases,
        known_articles=known_articles,
    )

    facts = join_section(paragraphs, "facts")
    legal_issue = infer_legal_issue(text, extracted.cited_articles, extracted.keywords)
    court_reasoning = join_section(paragraphs, "reasoning")
    conclusion = join_section(paragraphs, "order") or outcome_to_conclusion(extracted.outcome)
    facets = {
        **extracted.facets,
        **infer_domain_facets(text, case_name),
        "mvp_relevance": infer_mvp_relevance(
            text,
            case_name,
            extracted.cited_articles,
            extracted.keywords,
            extracted.facets,
        ),
    }
    material_facts = infer_material_facts(text, extracted.facets, extracted.outcome)
    aggravating_factors = infer_aggravating_factors(text)
    mitigating_factors = infer_mitigating_factors(text)
    key_disputed_facts = infer_key_disputed_facts(text)
    evidence_spans = {
        **extracted.evidence_spans,
        "facts": paragraph_evidence(paragraphs, "facts"),
        "court_reasoning": paragraph_evidence(paragraphs, "reasoning"),
        "conclusion": paragraph_evidence(paragraphs, "order"),
        "material_facts": material_fact_evidence(text, material_facts),
    }
    confidence = structure_confidence(
        extracted.confidence_score,
        facts=facts,
        reasoning=court_reasoning,
        material_facts=material_facts,
    )
    hash_payload = repr(
        (
            extracted.cited_articles,
            facts,
            legal_issue,
            court_reasoning,
            conclusion,
            material_facts,
            extracted.outcome,
        )
    )
    return StructuredCase(
        cited_articles=extracted.cited_articles,
        facts=facts,
        legal_issue=legal_issue,
        court_reasoning=court_reasoning,
        conclusion=conclusion,
        material_facts=material_facts,
        aggravating_factors=aggravating_factors,
        mitigating_factors=mitigating_factors,
        key_disputed_facts=key_disputed_facts,
        outcome=extracted.outcome,
        facets=facets,
        evidence_spans=evidence_spans,
        confidence_score=confidence,
        review_status="pending" if confidence < 0.7 else "auto_structured",
        structure_hash=hashlib.sha256(hash_payload.encode("utf-8")).hexdigest(),
    )


def join_section(paragraphs: list[Paragraph], section_type: str, max_chars: int = 1600) -> str | None:
    parts = [paragraph.text for paragraph in paragraphs if paragraph.section_type == section_type]
    if not parts:
        return None
    return " ".join(parts)[:max_chars]


def paragraph_evidence(paragraphs: list[Paragraph], section_type: str) -> list[dict[str, Any]]:
    return [
        {
            "paragraph_id": paragraph.paragraph_id,
            "char_start": paragraph.char_start,
            "char_end": paragraph.char_end,
        }
        for paragraph in paragraphs
        if paragraph.section_type == section_type
    ]


def infer_legal_issue(text: str, cited_articles: list[dict[str, Any]], keywords: list[str]) -> str | None:
    issues: list[str] = []
    refs = [article["normalized_ref"] for article in cited_articles]

    # 민사 쟁점
    if "민법_제750조" in refs:
        issues.append("불법행위 손해배상책임 성립")
    if "민법_제396조" in refs or "과실상계" in keywords:
        issues.append("과실상계 및 손해배상액 제한")
    if "민법_제751조" in refs or "위자료" in keywords:
        issues.append("재산 이외 손해와 위자료")
    if "민법_제393조" in refs:
        issues.append("손해배상 범위")
    if "자동차손해배상 보장법_제3조" in refs or "교통사고" in text:
        issues.append("자동차 운행자 손해배상책임")

    # 형사 쟁점
    if "형법_제250조" in refs or "살인" in text:
        issues.append("살인죄 성립 여부")
    if "형법_제257조" in refs or "형법_제258조의2" in refs:
        issues.append("상해죄 성립 및 죄책")
    if "형법_제260조" in refs or "형법_제261조" in refs:
        issues.append("폭행죄 성립 여부")
    if "형법_제347조" in refs or "사기" in text:
        issues.append("사기죄 성립 및 기망행위")
    if "형법_제355조" in refs or "형법_제356조" in refs:
        issues.append("횡령·배임죄 성립 여부")
    if "형법_제329조" in refs or "형법_제330조" in refs:
        issues.append("절도죄 성립 여부")
    if "형법_제297조" in refs or "형법_제298조" in refs:
        issues.append("성범죄 성립 및 처벌")
    if "도로교통법_제44조" in refs or "도로교통법_제148조의2" in refs or "음주운전" in text:
        issues.append("음주운전 성립 및 양형")
    if "형사소송법_제308조의2" in refs or "위법수집증거" in text:
        issues.append("위법수집증거 배제 여부")
    if "양형" in text or "집행유예" in text:
        issues.append("양형 및 집행유예 적정성")

    if issues:
        return ", ".join(issues)
    if keywords:
        return ", ".join(keywords[:3])
    return None


def infer_material_facts(
    text: str,
    facets: dict[str, Any],
    outcome: dict[str, Any],
) -> dict[str, Any]:
    event_type = infer_event_type(text)
    legal_domain = facets.get("legal_domain", "unknown")

    if legal_domain == "형사":
        return _infer_criminal_material_facts(text, event_type, outcome)

    return {
        "event_type": event_type,
        "legal_domain": legal_domain,
        "claim_type": "손해배상" if "손해배상" in text else None,
        "harm_type": facets.get("harm_type"),
        "causation_dispute": contains_any(text, ["인과관계", "상당인과관계"]),
        "negligence_dispute": contains_any(text, ["과실", "주의의무", "과실상계"]),
        "damage_scope_dispute": contains_any(text, ["손해액", "손해배상액", "손해의 범위", "일실수입", "치료비"]),
        "evidence_issue": contains_any(text, ["입증", "증거", "증명"]),
        "key_disputed_fact": infer_key_disputed_facts(text)[0] if infer_key_disputed_facts(text) else None,
        "outcome_disposition": outcome.get("disposition"),
    }


def _infer_criminal_material_facts(
    text: str,
    event_type: str | None,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    import re as _re
    sentence_term = outcome.get("sentence_term")
    crime_type = _infer_crime_type(text)
    return {
        "event_type": event_type or crime_type,
        "legal_domain": "형사",
        "crime_type": crime_type,
        "sentence_type": outcome.get("sentence_type"),
        "sentence_term": sentence_term,
        "suspended": outcome.get("suspended", False),
        "intent_dispute": contains_any(text, ["고의", "미필적 고의", "과실범", "고의성"]),
        "causation_dispute": contains_any(text, ["인과관계", "상당인과관계"]),
        "evidence_issue": contains_any(text, ["위법수집증거", "자백", "증거능력", "증거재판"]),
        "accomplice_dispute": contains_any(text, ["공동정범", "교사범", "방조범", "공범"]),
        "sentencing_dispute": contains_any(text, ["양형", "집행유예", "작량감경"]),
        "key_disputed_fact": _infer_criminal_disputed_fact(text),
        "outcome_disposition": outcome.get("disposition"),
    }


def _infer_crime_type(text: str) -> str | None:
    rules = [
        ("살인", ["살인", "살해", "피살"]),
        ("상해", ["상해", "부상"]),
        ("폭행", ["폭행", "폭력"]),
        ("사기", ["사기", "기망", "편취"]),
        ("횡령", ["횡령", "업무상횡령"]),
        ("배임", ["배임", "업무상배임"]),
        ("절도", ["절도", "절취", "야간주거침입"]),
        ("강도", ["강도", "강취"]),
        ("강간", ["강간", "성폭력", "강제추행", "준강간"]),
        ("음주운전", ["음주운전", "음주측정", "도로교통법"]),
        ("마약", ["마약", "향정신성", "대마"]),
        ("업무방해", ["업무방해", "위력"]),
    ]
    for crime, keywords in rules:
        if any(kw in text for kw in keywords):
            return crime
    return None


def _infer_criminal_disputed_fact(text: str) -> str | None:
    if contains_any(text, ["고의", "미필적 고의"]):
        return "범의(고의) 인정 여부"
    if contains_any(text, ["위법수집증거", "자백의 임의성"]):
        return "증거능력 및 증거 적법성"
    if contains_any(text, ["공동정범", "공범"]):
        return "공동정범 성립 여부"
    if contains_any(text, ["양형", "집행유예"]):
        return "적정 양형 판단"
    return None


def infer_domain_facets(text: str, case_name: str | None) -> dict[str, Any]:
    title = case_name or ""
    combined = f"{title} {text}"
    rules = [
        # 형사 (우선 배치 — 민사 키워드와 겹칠 수 있어 먼저 탐지)
        ("criminal_violent", ["살인", "상해", "폭행", "강도", "강간", "강제추행"]),
        ("criminal_property", ["절도", "사기", "횡령", "배임", "재물손괴"]),
        ("criminal_traffic", ["음주운전", "도로교통법", "교통사고처리특례법"]),
        ("criminal_drug", ["마약", "향정신성", "대마초"]),
        ("criminal_general", ["공소사실", "범죄사실", "피고인", "징역", "벌금", "집행유예"]),
        # 민사
        ("damages", ["손해배상", "불법행위", "위자료", "교통사고", "과실상계", "구상금"]),
        ("unjust_enrichment", ["부당이득", "부당이득금"]),
        ("lease", ["임대차", "보증금", "건물명도", "토지인도", "인도청구"]),
        ("labor", ["임금", "근로자지위", "해고", "파견근로", "퇴직금"]),
        ("inheritance", ["상속", "유류분", "상속분", "유언"]),
        ("tax", ["취득세", "조세", "부가가치세", "법인세", "소득세"]),
        ("property", ["소유권", "근저당", "말소등기", "이전등기", "점유"]),
        ("ip", ["특허", "실용신안", "상표", "저작권", "지식재산"]),
        ("contract", ["약정금", "매매대금", "물품대금", "공사대금", "채무불이행"]),
        ("insurance", ["보험금", "보험자", "구상금", "자동차손해배상 보장법"]),
        ("family", ["이혼", "재산분할", "친권", "양육"]),
    ]
    title_hits = [domain for domain, terms in rules if any(term in title for term in terms)]
    text_hits = [domain for domain, terms in rules if any(term in combined for term in terms)]
    ordered = dedupe(title_hits + text_hits)
    primary = ordered[0] if ordered else "general"
    return {
        "primary_domain": primary,
        "secondary_domains": ordered[1:],
        "issue_tags": infer_issue_tags(combined),
    }


def infer_issue_tags(text: str) -> list[str]:
    rules = [
        # 민사
        ("causation", ["인과관계", "상당인과관계"]),
        ("negligence", ["과실", "주의의무", "과실상계"]),
        ("damages_amount", ["손해액", "배상액", "일실수입", "치료비"]),
        ("limitation_period", ["소멸시효", "시효"]),
        ("restitution", ["부당이득", "반환"]),
        ("ownership", ["소유권", "등기", "점유"]),
        ("employment_status", ["근로자지위", "파견근로", "직접고용"]),
        ("wage", ["임금", "퇴직금", "수당"]),
        ("deposit", ["보증금", "임대차"]),
        ("inheritance_share", ["유류분", "상속분"]),
        ("tax_assessment", ["처분취소", "취득세", "과세"]),
        ("insurance_subrogation", ["구상금", "보험자", "대위"]),
        # 형사
        ("criminal_intent", ["고의", "미필적 고의", "범의"]),
        ("criminal_evidence", ["위법수집증거", "자백", "증거능력"]),
        ("criminal_accomplice", ["공동정범", "공범", "교사범", "방조범"]),
        ("criminal_sentencing", ["양형", "집행유예", "작량감경"]),
        ("criminal_selfdefense", ["정당방위", "긴급피난"]),
        ("criminal_drunk_driving", ["음주운전", "음주측정"]),
    ]
    return [tag for tag, terms in rules if any(term in text for term in terms)]


def infer_mvp_relevance(
    text: str,
    case_name: str | None,
    cited_articles: list[dict[str, Any]],
    keywords: list[str],
    facets: dict[str, Any],
) -> str:
    refs = {article.get("normalized_ref") for article in cited_articles}
    title = case_name or ""
    strong_refs = {
        "민법_제35조",
        "민법_제390조",
        "민법_제393조",
        "민법_제396조",
        "민법_제750조",
        "민법_제751조",
        "민법_제755조",
        "민법_제756조",
        "민법_제758조",
        "민법_제760조",
        "민법_제763조",
        "민법_제766조",
        "자동차손해배상 보장법_제3조",
    }
    weak_domain_terms = [
        "상속",
        "유류분",
        "이혼",
        "재산분할",
        "근저당",
        "소유권",
        "토지인도",
        "부당이득",
        "취득세",
        "조세",
        "임대차",
        "보험금",
        "임금",
        "근로자지위",
        "실용신안",
        "지식재산",
        "특허",
        "약정금",
        "배당이의",
        "하자보수",
        "횡령",
    ]
    core_title_terms = [
        "손해배상",
        "구상금",
        "보험금",
    ]
    core_fact_terms = [
        "교통사고",
        "자동차",
        "피해자 과실",
        "과실상계",
        "사용자책임",
        "피용자",
        "공동불법행위",
        "공작물",
        "위자료",
        "명예훼손",
        "치료비",
        "일실수입",
        "불법행위책임",
    ]
    damages_hits = sum(
        1
        for keyword in [
            "손해배상",
            "불법행위",
            "위자료",
            "과실상계",
            "교통사고",
            "자동차",
            "사용자책임",
            "공동불법행위",
            "공작물",
            "채무불이행",
        ]
        if keyword in text
    )
    has_core_title = any(term in title for term in core_title_terms)
    has_core_fact = any(term in text for term in core_fact_terms)
    has_weak_title = any(term in title for term in weak_domain_terms)

    if has_weak_title and not has_core_title:
        return "out_of_scope"
    if has_core_title and (refs & strong_refs or damages_hits >= 1):
        return "mvp_relevant"
    if refs & strong_refs and has_core_fact:
        return "mvp_relevant"
    if damages_hits >= 2 or (refs & strong_refs):
        return "weakly_related"
    if any(term in text for term in weak_domain_terms):
        return "out_of_scope"
    if keywords:
        return "weakly_related"
    return "out_of_scope"


def infer_event_type(text: str) -> str | None:
    # 형사
    if contains_any(text, ["살인", "살해", "피살"]):
        return "살인"
    if contains_any(text, ["강간", "강제추행", "성폭력"]):
        return "성범죄"
    if contains_any(text, ["음주운전", "음주측정"]):
        return "음주운전"
    if contains_any(text, ["사기", "기망", "편취"]):
        return "사기"
    if contains_any(text, ["횡령", "배임"]):
        return "횡령·배임"
    if contains_any(text, ["절도", "절취"]):
        return "절도"
    if contains_any(text, ["상해", "폭행"]):
        return "상해·폭행"
    # 민사
    if contains_any(text, ["교통사고", "자동차", "차량", "운행"]):
        return "교통사고"
    if contains_any(text, ["사용자책임", "피용자", "사무집행"]):
        return "사용자책임"
    if contains_any(text, ["공동불법행위", "공동", "각 피고"]):
        return "공동불법행위"
    if contains_any(text, ["명예", "정신상", "위자료"]):
        return "위자료"
    if contains_any(text, ["과실상계", "피해자 과실"]):
        return "과실상계"
    return None


def infer_aggravating_factors(text: str) -> list[str]:
    factors: list[str] = []
    if contains_any(text, ["고의", "반복", "중대한 과실"]):
        factors.append("가해 행위의 고의성 또는 중대성")
    if contains_any(text, ["주의의무 위반", "전방주시", "안전조치"]):
        factors.append("주의의무 위반")
    # 형사 가중 요소
    if contains_any(text, ["누범", "전과", "동종 전력"]):
        factors.append("누범 또는 동종 전과")
    if contains_any(text, ["범행 후 도주", "증거 인멸", "도주"]):
        factors.append("범행 후 도주 또는 증거인멸")
    if contains_any(text, ["피해 회복 없음", "합의 거부", "피해자 미합의"]):
        factors.append("피해 미회복 및 합의 미성립")
    return factors


def infer_mitigating_factors(text: str) -> list[str]:
    factors: list[str] = []
    if contains_any(text, ["피해자 과실", "과실상계"]):
        factors.append("피해자 과실 또는 과실상계")
    if contains_any(text, ["입증 부족", "증거 부족"]):
        factors.append("손해 또는 인과관계 입증 부족")
    # 형사 감경 요소
    if contains_any(text, ["초범", "전과 없음", "전과 없"]):
        factors.append("초범 또는 전과 없음")
    if contains_any(text, ["자백", "반성", "자수"]):
        factors.append("자백 또는 진지한 반성")
    if contains_any(text, ["피해 변제", "합의", "피해 회복"]):
        factors.append("피해 변제 또는 합의")
    if contains_any(text, ["집행유예", "작량감경"]):
        factors.append("집행유예 또는 작량감경 사유")
    return factors


def infer_key_disputed_facts(text: str) -> list[str]:
    disputed: list[str] = []
    # 민사
    if contains_any(text, ["과실상계", "피해자 과실"]):
        disputed.append("피해자 과실 및 과실상계 비율")
    if contains_any(text, ["인과관계", "상당인과관계"]):
        disputed.append("행위와 손해 사이의 상당인과관계")
    if contains_any(text, ["손해액", "일실수입", "치료비", "장래손해"]):
        disputed.append("손해 범위와 손해액 산정")
    if contains_any(text, ["입증", "증거 부족"]):
        disputed.append("주장 사실의 입증 정도")
    # 형사
    if contains_any(text, ["고의", "미필적 고의", "범의"]):
        disputed.append("범의(고의) 인정 여부")
    if contains_any(text, ["위법수집증거", "자백의 임의성"]):
        disputed.append("증거능력 및 위법수집증거 배제")
    if contains_any(text, ["공동정범", "공범 관계"]):
        disputed.append("공동정범 성립 범위")
    return disputed


def material_fact_evidence(text: str, material_facts: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for key, value in material_facts.items():
        if value in (None, False, "unknown"):
            continue
        token = str(value) if isinstance(value, str) else key_to_keyword(key)
        index = text.find(token)
        if index >= 0:
            evidence[key] = {"char_start": index, "char_end": index + len(token), "text": token}
    return evidence


def key_to_keyword(key: str) -> str:
    return {
        "causation_dispute": "인과관계",
        "negligence_dispute": "과실",
        "damage_scope_dispute": "손해",
        "evidence_issue": "입증",
    }.get(key, key)


def outcome_to_conclusion(outcome: dict[str, Any]) -> str | None:
    disposition = outcome.get("disposition")
    if not disposition or disposition == "unknown":
        return None
    return f"결론: {disposition}"


def structure_confidence(
    base_confidence: float,
    facts: str | None,
    reasoning: str | None,
    material_facts: dict[str, Any],
) -> float:
    score = base_confidence
    if facts:
        score += 0.05
    if reasoning:
        score += 0.05
    if any(value not in (None, False, "unknown") for value in material_facts.values()):
        score += 0.05
    return round(min(score, 0.95), 3)


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
