import numpy as np
import pandas as pd
import pytest
from scipy import sparse

from src.collaborative import BiasedMF
from src.research_embeddings import CachedEncoder, load_vectors, mean_pool, save_vectors
from src.research_models import (
    calibrate,
    content_contributions,
    content_scores,
    fold_in_scores,
    preference_weights,
)
from src.semantic import SemanticContent


def model():
    ratings = pd.DataFrame(
        [(u, m, 1 + (u + m) % 5) for u in range(1, 6) for m in range(1, 7)],
        columns=["user_id", "movie_id", "rating"],
    )
    return BiasedMF(factors=3, epochs=3, regularization=10).fit(ratings, np.arange(1, 8))


def test_fold_in_matches_production_and_does_not_mutate_factors():
    mf = model()
    original = mf.item_factors.copy()
    for profile in ({}, {100: 5}, {1: 1}, {1: 5, 2: 2, 4: 4}):
        np.testing.assert_allclose(fold_in_scores(mf, profile), mf.scores(profile), atol=1e-12)
        assert np.isfinite(fold_in_scores(mf, profile, "history_scaled")).all()
    np.testing.assert_array_equal(original, mf.item_factors)
    assert not np.allclose(
        fold_in_scores(mf, {1: 5}, 1), fold_in_scores(mf, {1: 5}, 30), rtol=0, atol=1e-10
    )
    for strength in (0, -1, np.nan):
        with pytest.raises(ValueError):
            fold_in_scores(mf, {1: 5}, strength)
    np.testing.assert_allclose(model().item_factors, mf.item_factors)


def test_candidate_only_percentiles_are_not_probabilities():
    score = np.array([999.0, 2.0, 2.0, 4.0])
    pool = np.array([1, 2, 3])
    np.testing.assert_allclose(calibrate(score, pool, "cf", "percentile"), [0.5, 0.25, 0.25, 1])
    np.testing.assert_allclose(calibrate(np.zeros(4), pool, "cf", "percentile"), 0.5)
    np.testing.assert_allclose(calibrate(score, pool, "cf"), [1, 0.25, 0.25, 0.75])


@pytest.mark.parametrize("matrix", [np.eye(3), sparse.csr_matrix(np.eye(3))])
@pytest.mark.parametrize("mode", ["signed", "positive_only", "user_centered"])
def test_signed_attributions_sum_to_actual_content_score(matrix, mode):
    positions = {1: 0, 2: 1, 3: 2}
    profile = {1: 5, 2: 1}
    score = content_scores(matrix, positions, profile, mode)
    for mid, i in positions.items():
        terms = content_contributions(matrix, positions, profile, mid, mode)
        assert sum(row["term"] for row in terms) == pytest.approx(score[i])
    assert content_scores(matrix, positions, {}, mode) is None
    assert content_scores(matrix, positions, {99: 4}, mode) is None
    if mode == "signed":
        assert score[0] > 0 > score[1]
        assert content_scores(matrix, positions, {1: 3}) is None
    if mode == "user_centered":
        assert content_scores(matrix, positions, {1: 5}, mode) is None


def test_missing_feedback_is_never_added_and_invalid_ratings_fail():
    np.testing.assert_allclose(preference_weights([1, 3, 5], "signed"), [-2, 0, 2])
    np.testing.assert_allclose(preference_weights([1, 3, 5], "positive_only"), [0, 0, 2])
    for value in (np.nan, 0, 6):
        with pytest.raises(ValueError):
            preference_weights([value], "signed")


def test_encoder_pooling_ignores_padding_and_runs_with_numpy_on_cpu():
    hidden = np.array([[[1.0, 0], [1.0, 0], [999.0, 999.0]], [[0.0, 2], [0.0, 0], [0.0, 0]]])
    np.testing.assert_allclose(mean_pool(hidden, [[1, 1, 0], [1, 0, 0]]), [[1, 0], [0, 1]])
    with pytest.raises(ValueError):
        mean_pool(hidden, np.zeros((2, 3)))
    with pytest.raises(ValueError):
        mean_pool(hidden, np.ones((2, 2)))


def test_embedding_artifact_requires_exact_catalog_text_encoder_and_finite_vectors(tmp_path):
    ids, texts = np.array([1, 2]), ["First Drama", "Second Comedy"]
    vectors = np.zeros((2, 384), dtype=np.float32)
    vectors[:, 0] = 1
    path = tmp_path / "vectors.npz"
    save_vectors(path, ids, vectors, texts)
    np.testing.assert_array_equal(load_vectors(path, ids, texts), vectors)
    for bad_ids, bad_text in ((ids[::-1], texts), (ids, ["Changed", "Second Comedy"])):
        with pytest.raises(ValueError):
            load_vectors(path, bad_ids, bad_text)
    bad = tmp_path / "bad.npz"
    save_vectors(bad, ids, np.full((2, 384), np.nan), texts)
    with pytest.raises(ValueError):
        load_vectors(bad, ids, texts)
    with pytest.raises(FileExistsError):
        save_vectors(path, ids, vectors, texts)
    with pytest.raises(FileNotFoundError):
        CachedEncoder(tmp_path)  # No download or runtime/API dependency.


def test_research_corpus_is_optional_and_does_not_change_lexical_scores(sample):
    movies, _ = sample
    baseline = SemanticContent(movies, dimensions=4)
    research = SemanticContent(movies, dimensions=4, retain_texts=True)
    assert not hasattr(baseline, "texts")
    assert len(research.texts) == len(movies)
    np.testing.assert_array_equal(baseline.features, research.features)
    np.testing.assert_array_equal(baseline.scores({1: 5, 7: 1}), research.scores({1: 5, 7: 1}))
