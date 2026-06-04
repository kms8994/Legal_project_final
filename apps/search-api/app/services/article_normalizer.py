from __future__ import annotations

import re
from dataclasses import dataclass


class ArticleParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedArticleRef:
    raw: str
    law_name: str
    article_no: int

    @property
    def normalized_ref(self) -> str:
        return f"{self.law_name}_제{self.article_no}조"


ARTICLE_RE = re.compile(
    r"^\s*(?P<law_name>[가-힣A-Za-z0-9·ㆍ\s]+?)\s*(?:제)?\s*(?P<article_no>\d+)\s*조\s*$"
)


def parse_article_ref(raw_query: str) -> ParsedArticleRef:
    compact = " ".join(raw_query.strip().split())
    match = ARTICLE_RE.match(compact)
    if match is None:
        raise ArticleParseError("조문은 '민법 제750조' 형식으로 입력해야 합니다.")

    law_name = match.group("law_name").replace(" ", "")
    article_no = int(match.group("article_no"))
    if article_no <= 0:
        raise ArticleParseError("조문 번호는 1 이상의 숫자여야 합니다.")

    return ParsedArticleRef(
        raw=raw_query,
        law_name=law_name,
        article_no=article_no,
    )
