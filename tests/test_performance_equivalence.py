"""Numerical and explanation regressions for engineering-only optimizations."""

import numpy as np
import pytest

from app.recommender import ALGORITHMS, Recommender
from src.ranking import rank_candidates


def reference_mmr(scores, indices, item_ids, features, k, diversity):
    """Pre-optimization formula, with the original stable tie ordering."""
    order = indices[np.lexsort((item_ids[indices], -scores[indices]))]
    if not diversity or len(order) < 2:
        return order[:k]
    values = scores[order]
    span = float(np.ptp(values))
    relevance = (values - values.min()) / span if span > 1e-12 else np.ones(len(values))
    chosen = []
    available = np.ones(len(order), dtype=bool)
    redundancy = np.zeros(len(order))
    for _ in range(min(k, len(order))):
        mmr = (1 - diversity) * relevance - diversity * redundancy
        mmr[~available] = -np.inf
        picked = int(np.argmax(mmr))
        chosen.append(int(order[picked]))
        available[picked] = False
        redundancy = np.maximum(redundancy, features[order] @ features[order[picked]])
    return np.asarray(chosen, dtype=int)


@pytest.mark.parametrize("diversity", [0, 0.2, 0.5, 1])
def test_mmr_matches_previous_formula_for_subsets_ties_and_empty_candidates(diversity):
    rng = np.random.default_rng(42)
    features = rng.random((100, 19))
    features /= np.linalg.norm(features, axis=1, keepdims=True)
    ids = rng.permutation(100)
    for scores in (rng.random(100), np.ones(100), rng.integers(1, 4, 100).astype(float)):
        for indices, k in (
            (np.arange(100), 10),
            (np.array([9, 3, 1, 7]), 10),
            (np.array([7]), 1),
            (np.array([], dtype=int), 10),
        ):
            np.testing.assert_array_equal(
                rank_candidates(scores, indices, ids, features, k, diversity),
                reference_mmr(scores, indices, ids, features, k, diversity),
            )


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_shared_explanations_match_individual_results_in_both_languages(
    sample, monkeypatch, algorithm
):
    engine = Recommender(*sample)
    profile = {1: 5, 2: 1, 3: 4}
    # Warm scoring before measuring explanation-specific calls.
    scores = engine.score_components(profile)[algorithm]
    for language in ("en", "uk"):
        expected = {
            int(mid): engine._result(i, float(scores[i]), profile, algorithm, language)
            for i, mid in enumerate(engine.movie_ids)
            if mid not in profile
        }
        original = engine.content.scores
        calls = []

        def counted(values):
            calls.append(dict(values))
            return original(values)

        with monkeypatch.context() as context:
            context.setattr(engine.content, "scores", counted)
            rows = engine.recommend(profile, algorithm, language=language, min_ratings=0)
        assert rows == [expected[row.movie_id] for row in rows]
        assert len(calls) == (1 if algorithm in ("Hybrid", "Content-based") else 0)


def test_neutral_profile_explanation_remains_popularity_fallback(sample):
    engine = Recommender(*sample)
    profile = {1: 3, 2: 3}
    scores = engine.score_components(profile)["Content-based"]
    rows = engine.recommend(profile, "Content-based", min_ratings=0)
    assert rows == [
        engine._result(
            engine.positions[row.movie_id],
            float(scores[engine.positions[row.movie_id]]),
            profile,
            "Content-based",
            "en",
        )
        for row in rows
    ]
