from __future__ import annotations

import hashlib
import importlib
import json
import math
import re
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any


EMBEDDING_DIMENSION = 768
LOCAL_EMBEDDING_MODEL = "local-hash-embedding-v1"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_LOCAL_MODEL = "dragonkue/multilingual-e5-small-ko"
EMBEDDING_MODEL = LOCAL_EMBEDDING_MODEL
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embedding_model_name(
    *,
    provider: str = "local",
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    if provider == "openai" and api_key:
        return model or DEFAULT_OPENAI_EMBEDDING_MODEL
    if provider in {"sentence-transformers", "huggingface"}:
        return model or DEFAULT_LOCAL_MODEL
    return LOCAL_EMBEDDING_MODEL


def embed_text(
    text: str,
    dimension: int = EMBEDDING_DIMENSION,
    *,
    provider: str = "local",
    model: str | None = None,
    api_key: str | None = None,
    input_type: str = "passage",
) -> list[float]:
    if provider == "openai" and api_key:
        return _embed_text_openai(
            text,
            api_key=api_key,
            model=model or DEFAULT_OPENAI_EMBEDDING_MODEL,
            dimension=dimension,
        )
    if provider in {"sentence-transformers", "huggingface"}:
        return _embed_text_sentence_transformers(
            text,
            model=model or DEFAULT_LOCAL_MODEL,
            dimension=dimension,
            input_type=input_type,
        )
    return _embed_text_local(text, dimension)


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _embed_text_local(text: str, dimension: int = EMBEDDING_DIMENSION) -> list[float]:
    vector = [0.0] * dimension
    tokens = _tokens(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def _embed_text_openai(
    text: str,
    *,
    api_key: str,
    model: str,
    dimension: int,
) -> list[float]:
    payload = json.dumps(
        {
            "model": model,
            "input": text,
            "dimensions": dimension,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_EMBEDDINGS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_body = json.loads(raw_body)
            error = error_body.get("error", {})
            message = error.get("message", raw_body)
            error_type = error.get("type", "unknown")
            code = error.get("code", "unknown")
        except json.JSONDecodeError:
            message = raw_body
            error_type = "unknown"
            code = "unknown"
        raise RuntimeError(
            f"OpenAI embeddings request failed: status={exc.code}, type={error_type}, "
            f"code={code}, message={message}"
        ) from exc

    embedding = body["data"][0]["embedding"]
    if len(embedding) != dimension:
        raise RuntimeError(f"Embedding dimension mismatch: expected {dimension}, got {len(embedding)}")
    return [float(value) for value in embedding]


def _embed_text_sentence_transformers(
    text: str,
    *,
    model: str,
    dimension: int,
    input_type: str,
) -> list[float]:
    sentence_transformers = importlib.import_module("sentence_transformers")
    sentence_transformer = sentence_transformers.SentenceTransformer
    encoder = _load_sentence_transformer(model, sentence_transformer)
    prepared_text = _prepare_sentence_transformer_text(text, model=model, input_type=input_type)
    embedding = encoder.encode(
        prepared_text,
        normalize_embeddings=True,
        convert_to_numpy=False,
        show_progress_bar=False,
    )
    vector = [float(value) for value in embedding]
    return _fit_dimension(vector, dimension)


@lru_cache(maxsize=2)
def _load_sentence_transformer(model: str, sentence_transformer_class: Any) -> Any:
    try:
        return sentence_transformer_class(model)
    except Exception as exc:
        raise RuntimeError(
            "Local embedding model could not be loaded. Install dependencies with "
            "`apps\\search-api\\.venv\\Scripts\\python.exe -m pip install sentence-transformers` "
            f"and ensure the model is available: {model}"
        ) from exc


def _prepare_sentence_transformer_text(text: str, *, model: str, input_type: str) -> str:
    if "e5" not in model.lower():
        return text
    prefix = "query" if input_type == "query" else "passage"
    return f"{prefix}: {text}"


def _fit_dimension(vector: list[float], dimension: int) -> list[float]:
    if len(vector) == dimension:
        return vector
    if len(vector) > dimension:
        return vector[:dimension]
    return vector + [0.0] * (dimension - len(vector))


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[0-9A-Za-z가-힣_]+", text)
        if len(token) >= 2
    ]
