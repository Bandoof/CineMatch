import numpy as np
import pytest

from app.recommender import ALGORITHMS, Recommender
from src.collaborative import BiasedMF
from src.data import fingerprint, load_movielens, temporal_split
from src.evaluation import evaluate_all, prepare_cohort, ranking_metrics


def test_fold_in_personalizes_and_reduces_error(sample):
    movies, ratings = sample
    model = BiasedMF(factors=4, epochs=10).fit(ratings, movies.movie_id)
    action = model.scores({1: 5, 7: 1})
    drama = model.scores({1: 1, 7: 5})
    assert action[:6].mean() > action[6:].mean()
    assert drama[6:].mean() > drama[:6].mean()
    errors = [(model.scores(user_id=int(r.user_id))[int(r.movie_id) - 1] - r.rating) ** 2
              for r in ratings.itertuples()]
    assert np.mean(errors) < np.mean((ratings.rating - ratings.rating.mean()) ** 2)


def test_persistence_and_fingerprint(sample, tmp_path):
    movies, ratings = sample
    model = BiasedMF(factors=4, epochs=3).fit(ratings, movies.movie_id)
    path = tmp_path / "model.npz"
    digest = fingerprint(movies, ratings)
    model.save(path, digest)
    loaded = BiasedMF.load(path, digest)
    np.testing.assert_allclose(loaded.scores({1: 5}), model.scores({1: 5}))
    changed = ratings.copy()
    changed.loc[0, "rating"] = 3
    with pytest.raises(ValueError, match="does not match"):
        BiasedMF.load(path, fingerprint(movies, changed))


def test_recommendations_exclude_seen_disliked_and_hidden(sample):
    movies, ratings = sample
    engine = Recommender(movies, ratings)
    for algorithm in ALGORITHMS:
        result = engine.recommend({1: 5, 2: 1}, algorithm, blocked={3}, genres=["Action"])
        assert result
        assert all(r.movie_id not in {1, 2, 3} and "Action" in r.genres for r in result)
        assert len({r.movie_id for r in result}) == len(result)
    assert engine.recommend(year_range=(2000, 2020)) == []
    assert engine.recommend({}, "Hybrid") == engine.recommend({}, "Popularity")
    with pytest.raises(ValueError):
        engine.recommend({1: float("nan")})


def test_neutral_content_fallback(sample):
    movies, ratings = sample
    engine = Recommender(movies, ratings)
    assert engine.content.scores({1: 3}) is None
    scores = engine.score_components({1: 3})
    np.testing.assert_array_equal(scores["Content-based"], engine.popularity.scores)
    assert np.isfinite(scores["Hybrid"]).all()


def test_global_temporal_boundary_and_cohort(sample):
    movies, ratings = sample
    train, val, test = temporal_split(ratings)
    assert train.timestamp.max() < val.timestamp.min() <= val.timestamp.max() < test.timestamp.min()
    engine = Recommender(movies, train)
    cohort, details = prepare_cohort(engine, val)
    assert details["excluded_new_users"] >= 1
    for indices, components, relevant in cohort:
        assert (engine.popularity.counts[indices] > 0).all()
        assert relevant
        assert all(np.isfinite(scores).all() for scores in components.values())
    # A chronological partition does not mutate the input observations.
    assert len(train) + len(val) + len(test) == len(ratings)


def test_metrics_have_correct_denominators():
    metrics = ranking_metrics([4, 1, 9], {1, 2}, k=3)
    assert metrics["precision"] == pytest.approx(1 / 3)
    assert metrics["recall"] == .5
    assert metrics["ndcg"] == pytest.approx((1 / np.log2(3)) / (1 + 1 / np.log2(3)))
    assert ranking_metrics([1], {1, 2}, k=10)["precision"] == .1


def test_loader_and_evaluation(dataset_dir):
    movies, ratings = load_movielens(dataset_dir)
    # Each existing user has held-out observations, for a meaningful synthetic ranking test.
    past = ratings[ratings.movie_id <= 8]
    future = ratings[ratings.movie_id > 8]
    metrics, details = evaluate_all(Recommender(movies, past), future)
    assert details["evaluated_users"] > 0
    assert details["unavailable_relevant_items"] == details["relevant_items"]
    for row in metrics.values():
        assert all(0 <= value <= 1 for value in row.values())
        assert row["recall@10"] == 0  # future-only movies cannot enter the candidate catalog


def test_timestamp_ties_never_cross_boundary(sample):
    _, ratings = sample
    ratings = ratings.copy()
    ratings["timestamp"] = ratings.timestamp // 7
    parts = temporal_split(ratings)
    assert set(parts[0].timestamp).isdisjoint(parts[1].timestamp)
    assert set(parts[1].timestamp).isdisjoint(parts[2].timestamp)
