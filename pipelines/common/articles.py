from __future__ import annotations

import re
from dataclasses import dataclass


class ArticleRefParseError(ValueError):
    pass


LAW_ALIASES = {
    # 민사
    "민법": "민법",
    "민 법": "민법",
    "자동차손해배상 보장법": "자동차손해배상 보장법",
    "자동차손해배상보장법": "자동차손해배상 보장법",
    "자동차손배법": "자동차손해배상 보장법",
    "자동차손해배상법": "자동차손해배상 보장법",
    "자배법": "자동차손해배상 보장법",
    "제조물 책임법": "제조물 책임법",
    "제조물책임법": "제조물 책임법",
    # 형사
    "형법": "형법",
    "형 법": "형법",
    "형사소송법": "형사소송법",
    "형소법": "형사소송법",
    "특정범죄 가중처벌 등에 관한 법률": "특정범죄가중처벌법",
    "특정범죄가중처벌 등에 관한 법률": "특정범죄가중처벌법",
    "특가법": "특정범죄가중처벌법",
    "특정경제범죄 가중처벌 등에 관한 법률": "특정경제범죄가중처벌법",
    "특경법": "특정경제범죄가중처벌법",
    "도로교통법": "도로교통법",
    "마약류 관리에 관한 법률": "마약류관리법",
    "마약류관리에 관한 법률": "마약류관리법",
    "성폭력범죄의 처벌 등에 관한 특례법": "성폭력처벌법",
    "성폭력처벌법": "성폭력처벌법",
    "아동·청소년의 성보호에 관한 법률": "아청법",
    "아동청소년성보호법": "아청법",
}


@dataclass(frozen=True)
class NormalizedArticleRef:
    raw: str
    law_name: str
    article_no: int
    article_branch_no: int | None = None

    @property
    def normalized_ref(self) -> str:
        return make_normalized_ref(self.law_name, self.article_no, self.article_branch_no)

    @property
    def display_ref(self) -> str:
        branch = f"의{self.article_branch_no}" if self.article_branch_no else ""
        return f"{self.law_name} 제{self.article_no}조{branch}"


def normalize_law_name(value: str) -> str:
    compact = normalize_query_text(value)
    compact_no_space = compact.replace(" ", "")
    for alias, official_name in LAW_ALIASES.items():
        if compact == alias or compact_no_space == alias.replace(" ", ""):
            return official_name
    return compact_no_space


def make_normalized_ref(
    law_name: str,
    article_no: int,
    article_branch_no: int | None = None,
) -> str:
    branch = f"의{article_branch_no}" if article_branch_no else ""
    return f"{normalize_law_name(law_name)}_제{article_no}조{branch}"


def normalize_query_text(value: str) -> str:
    return " ".join(str(value).strip().split())


def parse_article_ref(raw_query: str) -> NormalizedArticleRef:
    compact = normalize_query_text(raw_query)
    compact = re.sub(r"\s+", " ", compact)

    patterns = [
        r"^(?P<law_name>.+?)\s*제\s*(?P<article_no>\d+)\s*조(?:\s*의\s*(?P<branch_no>\d+))?$",
        r"^(?P<law_name>.+?)\s*제\s*(?P<article_no>\d+)(?:\s*의\s*(?P<branch_no>\d+))?$",
        r"^(?P<law_name>.+?)\s+(?P<article_no>\d+)\s*조?(?:\s*의\s*(?P<branch_no>\d+))?$",
        r"^(?P<law_name>.*?[가-힣])(?P<article_no>\d+)\s*조?(?:\s*의\s*(?P<branch_no>\d+))?$",
    ]
    for pattern in patterns:
        match = re.match(pattern, compact)
        if not match:
            continue
        law_name = normalize_law_name(match.group("law_name"))
        article_no = int(match.group("article_no"))
        branch_no = match.groupdict().get("branch_no")
        if article_no <= 0:
            raise ArticleRefParseError("조문 번호는 1 이상의 숫자여야 합니다.")
        return NormalizedArticleRef(
            raw=raw_query,
            law_name=law_name,
            article_no=article_no,
            article_branch_no=int(branch_no) if branch_no else None,
        )

    raise ArticleRefParseError(
        "조문은 '민법 제750조', '민법 750', '자배법 제3조' 같은 형식으로 입력해야 합니다."
    )


def known_article_refs_for_law(
    law_name: str,
    article_numbers: list[int],
) -> set[str]:
    return {make_normalized_ref(law_name, article_no) for article_no in article_numbers}
