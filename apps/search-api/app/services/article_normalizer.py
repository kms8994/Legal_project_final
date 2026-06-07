from __future__ import annotations

import re
from dataclasses import dataclass


class ArticleParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedArticleRef:
    law_name: str
    article_no: int
    clause: str | None
    normalized_ref: str


_LAW_ALIASES: dict[str, str] = {
    "민법": "민법",
    "형법": "형법",
    "상법": "상법",
    "민사소송법": "민사소송법",
    "형사소송법": "형사소송법",
    "행정소송법": "행정소송법",
    "자동차손해배상보장법": "자동차손해배상보장법",
    "자배법": "자동차손해배상보장법",
    "자동차손배법": "자동차손해배상보장법",
    "제조물책임법": "제조물책임법",
    "근로기준법": "근로기준법",
    "국가배상법": "국가배상법",
}

_PATTERN = re.compile(
    r"(?P<law>[가-힣A-Za-z0-9]+(?:법|법률))\s*제\s*(?P<article>\d+)조(?:의\s*(?P<sub>\d+))?",
    re.UNICODE,
)


def parse_article_ref(raw_query: str) -> ParsedArticleRef:
    raw = raw_query.strip()
    m = _PATTERN.search(raw)
    if not m:
        raise ArticleParseError(f"조문 형식을 인식할 수 없습니다: {raw!r}")

    raw_law = m.group("law")
    law_name = _LAW_ALIASES.get(raw_law, raw_law)
    article_no = int(m.group("article"))
    sub = m.group("sub")
    clause = f"의{sub}" if sub else None

    suffix = f"제{article_no}조"
    if clause:
        suffix += clause
    normalized_ref = f"{law_name}_{suffix}"

    return ParsedArticleRef(
        law_name=law_name,
        article_no=article_no,
        clause=clause,
        normalized_ref=normalized_ref,
    )
