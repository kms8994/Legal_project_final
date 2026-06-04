from __future__ import annotations

from pipelines.common.text import normalize_case_text, split_case_text


def test_normalize_case_text_strips_html_and_preserves_korean() -> None:
    raw = "<p>【주 문】 원고의 청구를 일부 인용한다.</p><br/>【이 유】 1. 기초사실 원고는 상해를 입었다."

    normalized = normalize_case_text(raw)

    assert "<p>" not in normalized
    assert "【주 문】 원고의 청구를 일부 인용한다." in normalized
    assert "【이 유】 1. 기초사실 원고는 상해를 입었다." in normalized


def test_split_case_text_infers_sections_and_offsets() -> None:
    raw = "【주 문】 원고의 청구를 일부 인용한다. 【이 유】 1. 기초사실 원고는 사고로 상해를 입었다. 2. 판단 피고의 과실이 인정된다."

    paragraphs = split_case_text(raw)

    assert [paragraph.section_type for paragraph in paragraphs] == [
        "order",
        "facts",
        "reasoning",
    ]
    assert paragraphs[0].paragraph_id == "P0001"
    assert paragraphs[0].text == "원고의 청구를 일부 인용한다."
    assert raw[paragraphs[0].char_start : paragraphs[0].char_end] == paragraphs[0].text
