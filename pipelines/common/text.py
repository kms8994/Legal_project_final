from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


SECTION_HEADINGS = {
    "주문": "order",
    "청구취지": "claim",
    "항소취지": "claim",
    "상고취지": "claim",
    "이유": "reasoning",
    "판단": "reasoning",
    "사실": "facts",
    "기초사실": "facts",
    "인정사실": "facts",
    "쟁점": "issue",
}


@dataclass(frozen=True)
class Paragraph:
    paragraph_id: str
    section_type: str
    paragraph_order: int
    text: str
    char_start: int
    char_end: int
    content_hash: str


def strip_html(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def normalize_case_text(value: str) -> str:
    text = strip_html(value)
    text = text.replace("\u00a0", " ")
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"([【\[])\s+", r"\1", text)
    text = re.sub(r"\s+([】\]])", r"\1", text)
    return text.strip()


def source_hash(text: str) -> str:
    normalized = normalize_case_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def split_case_text(value: str) -> list[Paragraph]:
    text = normalize_case_text(value)
    prepared = add_split_markers(text)
    raw_parts = [part.strip() for part in prepared.split("\n") if part.strip()]

    paragraphs: list[Paragraph] = []
    search_from = 0
    current_section = "unknown"
    for raw_part in raw_parts:
        section = infer_section_type(raw_part, current_section)
        if is_section_heading(raw_part):
            current_section = section
            continue
        if section != "unknown":
            current_section = section

        start = text.find(raw_part, search_from)
        if start < 0:
            start = text.find(raw_part)
        if start < 0:
            start = search_from
        end = start + len(raw_part)
        search_from = end

        order = len(paragraphs) + 1
        content_hash = hashlib.sha256(raw_part.encode("utf-8")).hexdigest()
        paragraphs.append(
            Paragraph(
                paragraph_id=f"P{order:04d}",
                section_type=current_section,
                paragraph_order=order,
                text=raw_part,
                char_start=start,
                char_end=end,
                content_hash=content_hash,
            )
        )
    return paragraphs


def add_split_markers(text: str) -> str:
    marked = re.sub(r"\s*(【[^】]{1,30}】)", r"\n\1\n", text)
    marked = re.sub(r"\s+(?=(?:\d+|[가-하])\.\s)", "\n", marked)
    marked = re.sub(r"\s+(?=다\.\s)", "\n", marked)
    return marked


def infer_section_type(text: str, current_section: str = "unknown") -> str:
    heading = normalize_heading(text)
    if heading:
        for key, section_type in SECTION_HEADINGS.items():
            if key in heading:
                return section_type

    if re.match(r"^(?:가|나|다|라|마)\.\s", text) and current_section in {"reasoning", "facts"}:
        return current_section
    if any(keyword in text[:80] for keyword in ["사건의 개요", "기초사실", "인정사실"]):
        return "facts"
    if any(keyword in text[:80] for keyword in ["쟁점", "문제된다"]):
        return "issue"
    if any(keyword in text[:80] for keyword in ["판단", "살피건대", "이유로"]):
        return "reasoning"
    if any(keyword in text[:80] for keyword in ["주문", "기각한다", "인용한다", "파기한다"]):
        return "order"
    return current_section


def is_section_heading(text: str) -> bool:
    heading = normalize_heading(text)
    return bool(heading and len(heading) <= 30)


def normalize_heading(text: str) -> str | None:
    match = re.match(r"^【\s*([^】]+?)\s*】$", text)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    return None
