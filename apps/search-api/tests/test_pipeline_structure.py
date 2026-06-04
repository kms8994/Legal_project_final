from __future__ import annotations

from pipelines.common.structure import structure_case_text


def test_structure_case_text_builds_rule_fallback_structure() -> None:
    text = (
        "【주 문】 피고는 원고에게 손해배상액 일부를 지급하라. "
        "【이 유】 1. 기초사실 원고는 교통사고로 상해를 입었다. "
        "2. 판단 피고는 민법 제750조 및 자동차손해배상 보장법 제3조에 따른 책임이 있다. "
        "다만 피해자 과실과 과실상계를 참작한다."
    )

    structured = structure_case_text(text, case_type="민사", court_level="지방법원")

    refs = [article["normalized_ref"] for article in structured.cited_articles]
    assert "민법_제750조" in refs
    assert "자동차손해배상 보장법_제3조" in refs
    assert structured.facts is not None
    assert structured.court_reasoning is not None
    assert structured.conclusion is not None
    assert structured.material_facts["event_type"] == "교통사고"
    assert structured.material_facts["negligence_dispute"] is True
    assert "자동차 운행자 손해배상책임" in (structured.legal_issue or "")
    assert structured.evidence_spans["facts"]
    assert structured.confidence_score >= 0.7


def test_structure_case_text_marks_sparse_text_pending() -> None:
    structured = structure_case_text("사건 내용이 거의 없다.")

    assert structured.review_status == "pending"
    assert structured.confidence_score < 0.7
