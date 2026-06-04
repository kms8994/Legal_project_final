from __future__ import annotations

from pipelines.common.embedding import (
    DEFAULT_OPENAI_EMBEDDING_MODEL,
    DEFAULT_LOCAL_MODEL,
    EMBEDDING_DIMENSION,
    LOCAL_EMBEDDING_MODEL,
    content_hash,
    embed_text,
    embedding_model_name,
    vector_literal,
)
from pipelines.embed import build_case_contents, embed_preview


def test_embed_text_is_deterministic_and_normalized() -> None:
    first = embed_text("traffic accident negligence damages")
    second = embed_text("traffic accident negligence damages")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSION
    assert sum(1 for value in first if value != 0) > 0
    assert abs(sum(value * value for value in first) - 1.0) < 0.0001


def test_empty_embedding_returns_zero_vector() -> None:
    vector = embed_text("")

    assert len(vector) == EMBEDDING_DIMENSION
    assert all(value == 0 for value in vector)


def test_vector_literal_matches_pgvector_shape() -> None:
    literal = vector_literal([0.1, -0.2, 0.0])

    assert literal == "[0.10000000,-0.20000000,0.00000000]"


def test_build_case_contents_includes_expected_embedding_types() -> None:
    contents = dict(
        build_case_contents(
            {
                "facts": "facts text",
                "legal_issue": "issue text",
                "court_reasoning": "reasoning text",
                "conclusion": "conclusion text",
                "material_facts": {"victim_fault": True},
                "outcome": {"disposition": "accepted"},
            }
        )
    )

    assert set(contents) == {"facts", "issue", "material_facts", "combined"}
    assert "facts text" in contents["combined"]
    assert "victim_fault" in contents["material_facts"]


def test_embed_preview_exposes_hash_and_prefix() -> None:
    preview = embed_preview("sample text")

    assert preview["embedding_dimension"] == EMBEDDING_DIMENSION
    assert preview["content_hash"] == content_hash("sample text")
    assert len(preview["vector_prefix"]) == 8


def test_embedding_model_name_falls_back_without_openai_key() -> None:
    assert embedding_model_name(provider="openai", model=DEFAULT_OPENAI_EMBEDDING_MODEL) == LOCAL_EMBEDDING_MODEL


def test_embedding_model_name_uses_openai_with_key() -> None:
    assert (
        embedding_model_name(
            provider="openai",
            model=DEFAULT_OPENAI_EMBEDDING_MODEL,
            api_key="test-key",
        )
        == DEFAULT_OPENAI_EMBEDDING_MODEL
    )


def test_embedding_model_name_uses_sentence_transformers_model() -> None:
    assert embedding_model_name(provider="sentence-transformers") == DEFAULT_LOCAL_MODEL
