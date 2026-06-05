from __future__ import annotations

import pytest

from app.services.article_normalizer import ArticleParseError, parse_article_ref


def test_parse_article_ref_normalizes_common_statute_query() -> None:
    parsed = parse_article_ref(" 민법   제750조 ")

    assert parsed.law_name == "민법"
    assert parsed.article_no == 750
    assert parsed.normalized_ref == "민법_제750조"


@pytest.mark.parametrize(
    ("query", "normalized_ref"),
    [
        ("민법 750", "민법_제750조"),
        ("민법 제750", "민법_제750조"),
        ("민법750조", "민법_제750조"),
        ("민 법 750", "민법_제750조"),
        ("자배법 제3조", "자동차손해배상 보장법_제3조"),
        ("자동차손배법 3", "자동차손해배상 보장법_제3조"),
        ("자동차손해배상보장법 제3", "자동차손해배상 보장법_제3조"),
        ("자동차손배법 제12조의2", "자동차손해배상 보장법_제12조의2"),
        ("제조물책임법 제3조", "제조물 책임법_제3조"),
    ],
)
def test_parse_article_ref_accepts_flexible_user_input(
    query: str,
    normalized_ref: str,
) -> None:
    parsed = parse_article_ref(query)

    assert parsed.normalized_ref == normalized_ref


def test_parse_article_ref_rejects_free_text() -> None:
    with pytest.raises(ArticleParseError):
        parse_article_ref("교통사고 손해배상")
