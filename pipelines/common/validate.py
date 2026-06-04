from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    review_status: str
    confidence_score: float
    reasons: list[str]
    is_valid: bool


def validate_structure(
    structure: dict[str, Any],
    known_articles: set[str],
    text_length: int | None = None,
) -> ValidationResult:
    reasons: list[str] = []
    cited_articles = as_list(structure.get("cited_articles"))
    outcome = as_dict(structure.get("outcome"))
    facets = as_dict(structure.get("facets"))
    evidence_spans = as_dict(structure.get("evidence_spans"))
    confidence = parse_confidence(structure.get("confidence_score"))

    if not cited_articles:
        reasons.append("cited_articles_empty")

    for article in cited_articles:
        normalized_ref = as_dict(article).get("normalized_ref")
        if not normalized_ref:
            reasons.append("cited_article_missing_normalized_ref")
        elif normalized_ref not in known_articles:
            reasons.append(f"cited_article_unknown:{normalized_ref}")

    if outcome.get("direction") in (None, "", "unknown"):
        reasons.append("outcome_direction_unknown")
    if outcome.get("disposition") in (None, "", "unknown"):
        reasons.append("outcome_disposition_unknown")

    if facets.get("legal_domain") in (None, "", "unknown"):
        reasons.append("legal_domain_unknown")

    article_evidence = as_list(evidence_spans.get("cited_articles"))
    if cited_articles and not article_evidence:
        reasons.append("cited_articles_evidence_missing")
    validate_evidence_spans("cited_articles", article_evidence, text_length, reasons)

    outcome_evidence = evidence_spans.get("outcome")
    if outcome.get("direction") not in (None, "", "unknown") and not outcome_evidence:
        reasons.append("outcome_evidence_missing")
    if isinstance(outcome_evidence, dict):
        validate_evidence_spans("outcome", [outcome_evidence], text_length, reasons)

    adjusted_confidence = adjust_confidence(confidence, reasons)
    if adjusted_confidence < 0.7:
        reasons.append("confidence_below_threshold")

    unique_reasons = dedupe(reasons)
    if not unique_reasons:
        return ValidationResult(
            review_status="auto_validated",
            confidence_score=round(adjusted_confidence, 3),
            reasons=[],
            is_valid=True,
        )

    status = "needs_review"
    if has_hard_failure(unique_reasons):
        status = "invalid"
    return ValidationResult(
        review_status=status,
        confidence_score=round(adjusted_confidence, 3),
        reasons=unique_reasons,
        is_valid=False,
    )


def validate_evidence_spans(
    field_name: str,
    spans: list[Any],
    text_length: int | None,
    reasons: list[str],
) -> None:
    for span in spans:
        current = as_dict(span)
        start = current.get("char_start")
        end = current.get("char_end")
        if not isinstance(start, int) or not isinstance(end, int):
            reasons.append(f"{field_name}_evidence_offset_missing")
            continue
        if start < 0 or end <= start:
            reasons.append(f"{field_name}_evidence_offset_invalid")
            continue
        if text_length is not None and end > text_length:
            reasons.append(f"{field_name}_evidence_offset_out_of_range")


def adjust_confidence(confidence: float, reasons: list[str]) -> float:
    penalty = 0.0
    for reason in reasons:
        if reason.startswith("cited_article_unknown"):
            penalty += 0.2
        elif reason in {"cited_articles_empty", "outcome_direction_unknown"}:
            penalty += 0.15
        elif reason.endswith("_evidence_missing"):
            penalty += 0.1
        elif reason.endswith("_offset_invalid") or reason.endswith("_offset_out_of_range"):
            penalty += 0.1
        else:
            penalty += 0.05
    return max(confidence - penalty, 0.0)


def has_hard_failure(reasons: list[str]) -> bool:
    hard_prefixes = [
        "cited_article_missing_normalized_ref",
        "cited_articles_evidence_offset_invalid",
        "cited_articles_evidence_offset_out_of_range",
        "outcome_evidence_offset_invalid",
        "outcome_evidence_offset_out_of_range",
    ]
    return any(any(reason.startswith(prefix) for prefix in hard_prefixes) for reason in reasons)


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def parse_confidence(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
