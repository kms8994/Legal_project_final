from __future__ import annotations

import pytest

from app.services.article_normalizer import ArticleParseError, parse_article_ref


def test_parse_article_ref_normalizes_common_statute_query() -> None:
    parsed = parse_article_ref(" 민법   제750조 ")

    assert parsed.law_name == "민법"
    assert parsed.article_no == 750
    assert parsed.normalized_ref == "민법_제750조"


def test_parse_article_ref_rejects_free_text() -> None:
    with pytest.raises(ArticleParseError):
        parse_article_ref("교통사고 손해배상")
