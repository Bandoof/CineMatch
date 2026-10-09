import json

import numpy as np
import pandas as pd
import pytest

from app.recommender import Recommender
from app.runtime import artifact_signature, load_runtime, valid_report
from src.catalog import canonical_catalog, latest_ratings
from src.data import fingerprint, load_movielens
from src.evaluation import bootstrap_intervals, onboarding_evaluation
from src.i18n import EN, UK, genre_name
from src.profiles import MAX_PROFILE_BYTES, ProfileStore, export_profile, import_profile
from src.ranking import rank_candidates
from src.series import SERIES_COLUMNS, parse_show


@pytest.fixture
def with_series(sample):
    movies, ratings = sample
    shows = [{"id": sid, "name": name, "type": "Scripted", "premiered": "2010-01-01",
              "genres": genres, "rating": {"average": value},
              "url": f"https://www.tvmaze.com/shows/{sid}/test"}
             for sid, name, genres, value in [(1, "Test space", ["Science-Fiction"], 8),
                                              (2, "Test romance", ["Romance"], 9),
                                              (3, "Test unrated", ["Drama"], None)]]
    series = pd.DataFrame([parse_show(show) for show in shows], columns=SERIES_COLUMNS)
    return Recommender(movies, ratings, series=series)


def test_duplicate_identity_exclusion_and_event_boundaries(sample):
    movies, ratings = sample
    movies = movies.copy()
    movies["imdb_url"] = [f"https://example.com/{mid}" for mid in movies.movie_id]
    movies.loc[1, ["title", "imdb_url"]] = movies.loc[0, ["title", "imdb_url"]].values
    events = pd.DataFrame([(1, 1, 5, 1), (1, 2, 1, 100)],
                          columns=["user_id", "movie_id", "rating", "timestamp"])
    catalog, observations, aliases = canonical_catalog(movies, events)
    assert len(catalog) == 11 and aliases[2] == 1
    assert len(observations) == 2
    assert latest_ratings(observations[observations.timestamp < 100]).rating.tolist() == [5]
    assert latest_ratings(observations).rating.tolist() == [1]
    engine = Recommender(movies, ratings)
    for model in ENGLISH_MODELS:
        assert all(row.movie_id not in {1, 2, 3}
                   for row in engine.recommend({2: 5}, model, blocked={3}))
    assert import_profile(engine, '{"2": 5}')[0] == {1: 5}
    with pytest.raises(ValueError, match="Conflicting"):
        engine.validate_profile({1: 5, 2: 1})
    # Matching names with different metadata identities remain distinct.
    movies.loc[1, "imdb_url"] = "https://example.com/remake"
    assert len(canonical_catalog(movies, ratings)[0]) == 12


ENGLISH_MODELS = ("Popularity", "Content-based", "Collaborative", "Item-KNN", "Hybrid")


def test_series_type_filter_personalization_and_honest_scores(with_series):
    engine = with_series
    series = engine.recommend({}, media_type="Series", min_ratings=500)
    assert len(series) == 3
    assert all(row.movie_id < 0 and row.rating_count == 0 and row.rating_scale == 10 for row in series)
    assert next(row for row in series if row.movie_id == -3).average_rating is None
    assert all(row.movie_id > 0 for row in engine.recommend({}, media_type="Movie"))
    action = engine.score_components({-1: 5, -2: 1})
    romance = engine.score_components({-1: 1, -2: 5})
    assert action["Content-based"][engine.positions[1]] > romance["Content-based"][engine.positions[1]]
    np.testing.assert_array_equal(action["Collaborative"][:engine.film_count],
                                  romance["Collaborative"][:engine.film_count])
    results = engine.recommend({-1: 5}, "Hybrid", media_type="Series", language="uk")
    assert all(row.movie_id != -1 and "жанров" in row.reason.lower() for row in results)


def test_series_metadata_and_complete_translation():
    assert EN.keys() == UK.keys()
    assert genre_name("Sci-Fi", "uk") == "Наукова фантастика"
    assert parse_show({"id": 1, "type": "Reality", "name": "Other"}) is None
    with pytest.raises(ValueError):
        parse_show({"id": 1, "type": "Scripted", "name": "Bad",
                    "rating": {"average": float("nan")}})


def test_profile_roundtrip_validation_and_storage(with_series, tmp_path):
    engine = with_series
    payload = export_profile(engine, {1: 5, -1: 4.5}, {2, -2})
    expected = ({1: 5, -1: 4.5}, {2, -2})
    assert import_profile(engine, payload.encode("utf-8")) == expected
    name = "Мій профіль '; DROP TABLE profiles; --"
    path = tmp_path / "profiles.sqlite3"
    ProfileStore(path).save(name, payload)
    assert ProfileStore(path).names() == [name]
    assert import_profile(engine, ProfileStore(path).load(name)) == expected
    for invalid in ('{"1": NaN}', '{"1": true}', '{"9999": 4}', '[]',
                    'x' * (MAX_PROFILE_BYTES + 1)):
        with pytest.raises((ValueError, TypeError)):
            import_profile(engine, invalid)
    doc = json.loads(payload)
    doc["ratings"].append({"item_id": 1, "rating": 1})
    with pytest.raises(ValueError, match="Conflicting"):
        import_profile(engine, json.dumps(doc))


def test_diversity_reordering_keeps_relevance_at_zero():
    ids = np.arange(1, 5)
    scores = np.asarray([1, .99, .98, .9])
    features = np.asarray([[1, 0], [1, 0], [1, 0], [0, 1]])
    candidates = np.arange(4)
    assert rank_candidates(scores, candidates, ids, features, 2, 0).tolist() == [0, 1]
    assert rank_candidates(scores, candidates, ids, features, 2, .75).tolist() == [0, 3]


def test_item_knn_uses_observed_rating_patterns(sample):
    engine = Recommender(*sample)
    action = engine.score_components({1: 5, 7: 1})["Item-KNN"]
    drama = engine.score_components({1: 1, 7: 5})["Item-KNN"]
    assert action[1:6].mean() > action[7:].mean()
    assert drama[7:].mean() > drama[1:6].mean()


def test_cache_refreshes_new_and_modified_benchmark(dataset_dir):
    movies, ratings = load_movielens(dataset_dir)
    series_file = dataset_dir / "missing.json"
    report_file = dataset_dir / "reports" / "metrics.json"
    paths = [dataset_dir / "u.data", dataset_dir / "u.item", series_file, report_file]
    before = artifact_signature(paths)
    args = (str(dataset_dir), str(series_file), str(dataset_dir))
    assert load_runtime(*args, before)[1] is None
    report_file.parent.mkdir()
    report = {"fingerprint": fingerprint(movies, ratings), "protocol_version": 2,
              "selected_alpha": .25,
              "metrics": {model: {key: .1 for key in
                          ("precision@10", "recall@10", "ndcg@10", "coverage", "diversity")}
                          for model in ENGLISH_MODELS},
              "confidence_95": {model: {"ndcg@10": [0, .2]} for model in ENGLISH_MODELS},
              "test_cohort": {"evaluated_users": 3}, "onboarding": {"results": []},
              "diversity_analysis": []}
    report_file.write_text(json.dumps(report))
    created = artifact_signature(paths)
    assert created != before
    assert load_runtime(*args, created)[0].alpha == .25
    report["selected_alpha"] = .75
    report_file.write_text(json.dumps(report) + "\n")
    updated = artifact_signature(paths)
    assert updated != created
    assert load_runtime(*args, updated)[0].alpha == .75
    assert not valid_report([], fingerprint(movies, ratings))
    assert not valid_report({"fingerprint": fingerprint(movies, ratings)}, fingerprint(movies, ratings))


def test_bootstrap_pairs_users_and_handles_constant_difference():
    base = [{"precision": .1, "recall": .2, "ndcg": value} for value in (.1, .5, .9)]
    other = [{**row, "ndcg": row["ndcg"] + .05} for row in base]
    intervals, paired = bootstrap_intervals({"Popularity": base, "Hybrid": other})
    assert paired["Hybrid"] == pytest.approx([.05, .05])
    assert intervals["Hybrid"]["recall@10"] == pytest.approx([.2, .2])
    assert bootstrap_intervals({"Popularity": base, "Hybrid": other}) == (intervals, paired)


def test_onboarding_excludes_all_target_users(sample, monkeypatch):
    movies, ratings = sample
    past = ratings[ratings.movie_id <= 10].copy()
    future = ratings[ratings.movie_id > 10].copy()
    captured = []
    original = Recommender.score_components

    def observe(self, profile, user_id=None):
        captured.append((set(self.ratings.user_id), len(profile)))
        return original(self, profile, user_id)

    monkeypatch.setattr(Recommender, "score_components", observe)
    report = onboarding_evaluation(movies, past, future, .75, seed_counts=(3, 5))
    assert report["users"] > 0
    assert {count for _, count in captured} == {3, 5}
    excluded = set(report["excluded_training_user_ids"])
    assert all(not users.intersection(excluded) for users, _ in captured)
