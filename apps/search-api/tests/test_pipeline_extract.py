from __future__ import annotations

from pipelines.common.extract import extract_case_features


def test_extract_case_features_finds_articles_and_outcome() -> None:
    text = (
        "피고는 민법 제750조 및 제396조에 따라 손해배상책임을 부담한다. "
        "자동차손해배상 보장법 제3조도 참조된다. "
        "법원은 원고의 청구를 일부 인용한다."
    )

    extracted = extract_case_features(text, case_type="민사", court_level="대법원")

    refs = [article["normalized_ref"] for article in extracted.cited_articles]
    assert refs == [
        "민법_제750조",
        "민법_제396조",
        "자동차손해배상 보장법_제3조",
    ]
    assert extracted.outcome["disposition"] == "일부 인용"
    assert extracted.facets["legal_domain"] == "손해배상"
    assert extracted.evidence_spans["cited_articles"][0]["text"] == "민법 제750조"
    assert extracted.confidence_score >= 0.7


def test_extract_case_features_skips_unknown_bare_articles() -> None:
    text = "제999조가 언급되었지만 MVP 조문 범위에는 없다. 민법 제751조는 위자료 조항이다."

    extracted = extract_case_features(text)

    refs = [article["normalized_ref"] for article in extracted.cited_articles]
    assert refs == ["민법_제751조"]


def test_extract_case_features_uses_shared_law_alias_normalization() -> None:
    text = "자배법 제3조와 자동차손배법 3조는 자동차 사고 손해배상 책임의 근거로 언급되었다."

    extracted = extract_case_features(text)

    refs = [article["normalized_ref"] for article in extracted.cited_articles]
    assert refs == ["자동차손해배상 보장법_제3조"]
