from __future__ import annotations

from pipelines.common.validate import validate_structure


def test_validate_structure_auto_validates_good_rule_extract() -> None:
    structure = {
        "cited_articles": [{"normalized_ref": "민법_제750조"}],
        "outcome": {"disposition": "일부 인용", "direction": "원고 일부 승소"},
        "facets": {"legal_domain": "손해배상"},
        "evidence_spans": {
            "cited_articles": [{"char_start": 0, "char_end": 8, "text": "민법 제750조"}],
            "outcome": {"char_start": 20, "char_end": 25, "text": "일부 인용"},
        },
        "confidence_score": 0.75,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=40)

    assert result.review_status == "auto_validated"
    assert result.is_valid is True
    assert result.reasons == []
    assert result.categories == []
    assert result.primary_category is None


def test_validate_structure_marks_unknown_article_needs_review() -> None:
    structure = {
        "cited_articles": [{"normalized_ref": "민법_제999조"}],
        "outcome": {"disposition": "인용", "direction": "원고 승소"},
        "facets": {"legal_domain": "손해배상"},
        "evidence_spans": {
            "cited_articles": [{"char_start": 0, "char_end": 8, "text": "민법 제999조"}],
            "outcome": {"char_start": 20, "char_end": 22, "text": "인용"},
        },
        "confidence_score": 0.8,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=40)

    assert result.review_status == "needs_review"
    assert "cited_article_unknown:민법_제999조" in result.reasons
    assert result.categories == ["missing_scope"]
    assert result.primary_category == "missing_scope"
    assert result.confidence_score < 0.8


def test_validate_structure_marks_missing_fields_needs_review() -> None:
    structure = {
        "cited_articles": [],
        "outcome": {"disposition": "unknown", "direction": "unknown"},
        "facets": {"legal_domain": "unknown"},
        "evidence_spans": {},
        "confidence_score": 0.6,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=20)

    assert result.review_status == "needs_review"
    assert "cited_articles_empty" in result.reasons
    assert "outcome_direction_unknown" in result.reasons
    assert "confidence_below_threshold" in result.reasons
    assert result.categories == ["quality_issue", "out_of_scope", "low_confidence"]
    assert result.primary_category == "quality_issue"


def test_validate_structure_classifies_unknown_valid_article_as_missing_scope() -> None:
    structure = {
        "cited_articles": [{"normalized_ref": "민법_제756조"}],
        "outcome": {"disposition": "인용", "direction": "원고 승소"},
        "facets": {"legal_domain": "손해배상"},
        "evidence_spans": {
            "cited_articles": [{"char_start": 0, "char_end": 8, "text": "민법 제756조"}],
            "outcome": {"char_start": 20, "char_end": 22, "text": "인용"},
        },
        "confidence_score": 0.8,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=40)

    assert "cited_article_unknown:민법_제756조" in result.reasons
    assert "missing_scope" in result.categories
    assert result.primary_category == "missing_scope"


def test_validate_structure_classifies_citation_extraction_failure_as_quality_issue() -> None:
    structure = {
        "cited_articles": [],
        "outcome": {"disposition": "인용", "direction": "원고 승소"},
        "facets": {"legal_domain": "손해배상"},
        "evidence_spans": {
            "outcome": {"char_start": 20, "char_end": 22, "text": "인용"},
        },
        "confidence_score": 0.8,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=40)

    assert "cited_articles_empty" in result.reasons
    assert "quality_issue" in result.categories
    assert result.primary_category == "quality_issue"


def test_validate_structure_classifies_unknown_legal_domain_as_out_of_scope() -> None:
    structure = {
        "cited_articles": [{"normalized_ref": "민법_제750조"}],
        "outcome": {"disposition": "인용", "direction": "원고 승소"},
        "facets": {"legal_domain": "unknown"},
        "evidence_spans": {
            "cited_articles": [{"char_start": 0, "char_end": 8, "text": "민법 제750조"}],
            "outcome": {"char_start": 20, "char_end": 22, "text": "인용"},
        },
        "confidence_score": 0.8,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=40)

    assert "legal_domain_unknown" in result.reasons
    assert result.categories == ["out_of_scope"]
    assert result.primary_category == "out_of_scope"


def test_validate_structure_classifies_low_confidence_only() -> None:
    structure = {
        "cited_articles": [{"normalized_ref": "민법_제750조"}],
        "outcome": {"disposition": "인용", "direction": "원고 승소"},
        "facets": {"legal_domain": "손해배상"},
        "evidence_spans": {
            "cited_articles": [{"char_start": 0, "char_end": 8, "text": "민법 제750조"}],
            "outcome": {"char_start": 20, "char_end": 22, "text": "인용"},
        },
        "confidence_score": 0.65,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=40)

    assert result.reasons == ["confidence_below_threshold"]
    assert result.categories == ["low_confidence"]
    assert result.primary_category == "low_confidence"


def test_validate_structure_prioritizes_explicit_out_of_scope_facet() -> None:
    structure = {
        "cited_articles": [],
        "outcome": {"disposition": "unknown", "direction": "unknown"},
        "facets": {"legal_domain": "unknown", "mvp_relevance": "out_of_scope"},
        "evidence_spans": {},
        "confidence_score": 0.4,
    }

    result = validate_structure(structure, {"민법_제750조"}, text_length=40)

    assert "quality_issue" in result.categories
    assert "out_of_scope" in result.categories
    assert result.primary_category == "out_of_scope"
