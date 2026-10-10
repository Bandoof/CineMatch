"""Explicit local cached-weight integration; default/CI tests require no downloads."""

import os

import numpy as np
import pytest

from src.research_embeddings import CachedEncoder, load_vectors, save_vectors


@pytest.mark.skipif(
    not os.environ.get("CINEMATCH_RESEARCH_MODEL_CACHE"),
    reason="Optional pinned weights not supplied",
)
def test_real_cached_cpu_encoder_is_finite_bilingual_and_reproducible(tmp_path):
    encoder = CachedEncoder(os.environ["CINEMATCH_RESEARCH_MODEL_CACHE"])
    texts = [
        "A detective investigates a crime.",
        "Детектив розслідує злочин.",
        "A romantic comedy.",
    ]
    features = encoder.encode(texts, batch_size=2)
    assert encoder.session.get_providers() == ["CPUExecutionProvider"]
    assert features.shape == (3, 384)
    np.testing.assert_allclose(np.linalg.norm(features, axis=1), 1, atol=1e-5)
    np.testing.assert_allclose(encoder.encode(texts, batch_size=2), features, atol=1e-6)
    assert features[0] @ features[1] > features[0] @ features[2]  # Sanity pair only.
    cache = tmp_path / "features.npz"
    save_vectors(cache, np.arange(3), features, texts)
    np.testing.assert_array_equal(load_vectors(cache, np.arange(3), texts), features)


@pytest.mark.skipif(
    not os.environ.get("CINEMATCH_RESEARCH_MODEL_CACHE"),
    reason="Optional pinned weights not supplied",
)
def test_real_encoder_uses_exact_lexical_corpus_and_reloads_offline(sample, tmp_path):
    from scripts.research_v12 import fit_content
    from src.semantic import SemanticContent

    movies, ratings = sample
    legacy = SemanticContent(movies, train_ids=set(ratings.movie_id))
    assert not hasattr(legacy, "texts")
    lexical, models, costs = fit_content(
        movies, ratings, tmp_path, os.environ["CINEMATCH_RESEARCH_MODEL_CACHE"]
    )
    assert len(lexical.texts) == len(movies)
    np.testing.assert_allclose(legacy.features, lexical.features)
    assert models["minilm"].shape == (len(movies), 384)
    assert costs["embedding_source"]["backend"].endswith("one thread")
    _, reloaded, _ = fit_content(movies, ratings, tmp_path, None)
    np.testing.assert_array_equal(reloaded["minilm"], models["minilm"])
