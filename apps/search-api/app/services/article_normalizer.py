from __future__ import annotations

from pipelines.common.articles import (
    ArticleRefParseError,
    NormalizedArticleRef as ParsedArticleRef,
    parse_article_ref as parse_common_article_ref,
)


class ArticleParseError(ValueError):
    pass


def parse_article_ref(raw_query: str) -> ParsedArticleRef:
    try:
        return parse_common_article_ref(raw_query)
    except ArticleRefParseError as exc:
        raise ArticleParseError(str(exc)) from exc
