import numpy as np
import pandas as pd
import pytest

from app.recommender import Recommender
from src.explanations import adaptive_parts, cosine_terms
from src.semantic import SemanticContent
from src.series import SERIES_COLUMNS, parse_show


@pytest.mark.parametrize("profile", [{}, {1: 5, 2: 1}, {1: 3}, {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}])
def test_adaptive_terms_equal_actual_scores_and_do_not_mutate_cache(sample, profile):
    engine = Recommender(*sample)
    engine.attach_content(
        SemanticContent(engine.movies, dimensions=4), {"3": [0.25, 0.25, 0.5], "5": [0, 0, 1]}
    )
    before = engine.score_components(profile)
    parts = adaptive_parts(engine, profile)
    np.testing.assert_allclose(
        sum(terms for _, terms in parts.values()), before["Adaptive"], atol=1e-12
    )
    for name, values in before.items():
        np.testing.assert_array_equal(values, engine.score_components(profile)[name])


@pytest.mark.parametrize("language", ["en", "uk"])
def test_pure_quality_policy_never_claims_personal_als_or_content(sample, language):
    engine = Recommender(*sample)
    engine.attach_content(SemanticContent(engine.movies, dimensions=4), {"5": [0, 0, 1]})
    profile = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
    result = engine.recommend(profile, algorithm="Adaptive", language=language)[0]
    assert ("community quality" if language == "en" else "якістю спільноти") in result.reason
    assert "ALS" not in result.reason and "LSA" not in result.reason
    assert "validation" not in result.reason


@pytest.mark.parametrize("semantic", [False, True])
def test_real_positive_and_negative_content_terms_match_score(sample, semantic):
    engine = Recommender(*sample)
    if semantic:
        engine.attach_content(SemanticContent(engine.movies, dimensions=4))
    features = engine.semantic.features if semantic else engine.content.features
    scores = (
        engine.semantic.scores({1: 5, 7: 1}) if semantic else engine.content.scores({1: 5, 7: 1})
    )
    for mid, i in engine.positions.items():
        terms = cosine_terms(features, engine.positions, {1: 5, 7: 1}, mid)
        assert sum(row["term"] for row in terms) == pytest.approx(scores[i])
        assert {row["seed_id"] for row in terms} == {1, 7}


def test_zero_genre_weight_does_not_explain_hybrid_with_genre_match(sample):
    engine = Recommender(*sample, alpha=1)
    reasons = [row.reason for row in engine.recommend({1: 5}, algorithm="Hybrid")]
    assert not any("shared" in reason.lower() or "Test film 1" in reason for reason in reasons)


def test_topic_discount_and_variety_are_explicit_heuristics(sample):
    engine = Recommender(*sample)
    before = engine.recommend({1: 5}, algorithm="Content-based")
    after = engine.recommend(
        {1: 5}, algorithm="Content-based", blocked={7}, topic_blocked={7}, diversity=0.5
    )
    assert all("Variety" in row.reason for row in after)
    assert any("Topic discount" in row.reason for row in after)
    plain = {row.movie_id: row.score for row in before}
    assert any(row.score < plain[row.movie_id] for row in after if row.movie_id in plain)


@pytest.mark.parametrize("profile", [{-1: 5}, {1: 5, -1: 1}, {1: 3, -1: 3}])
def test_adaptive_series_and_series_only_fallback_terms_match_real_scores(sample, profile):
    shows = [
        {
            "id": sid,
            "name": "Synthetic series",
            "type": "Scripted",
            "premiered": "2010-01-01",
            "genres": ["Drama"],
            "rating": {"average": 8},
            "url": f"https://www.tvmaze.com/shows/{sid}/test",
        }
        for sid in (1, 2)
    ]
    series = pd.DataFrame([parse_show(show) for show in shows], columns=SERIES_COLUMNS)
    engine = Recommender(*sample, series=series)
    engine.attach_content(SemanticContent(engine.movies, dimensions=4), {"3": [0.25, 0.25, 0.5]})
    parts = adaptive_parts(engine, profile)
    np.testing.assert_allclose(
        sum(terms for _, terms in parts.values()),
        engine.score_components(profile)["Adaptive"],
        atol=1e-12,
    )
    assert not parts["cf"][0][engine.is_series].any()
