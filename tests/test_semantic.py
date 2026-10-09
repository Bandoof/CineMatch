import json

import numpy as np
import pytest

from app.recommender import Recommender
from app.runtime import valid_v3
from src.profiles import export_profile, import_library_profile, import_topics
from src.semantic import SemanticContent


def document(movies):
    return {"schema_version": 1, "items": {str(row.movie_id): {
        "original_title": row.title,
        "summary_en": "astronaut spaceship orbit galaxy" if row.movie_id <= 6 else "friendship love family romance",
        "summary_uk": "космос астронавт подорож" if row.movie_id <= 6 else "дружба кохання родина",
        "source_url": "https://en.wikipedia.org/wiki/Test",
        "source_uk": "https://uk.wikipedia.org/wiki/Test"} for row in movies.itertuples()}}


def test_content_uses_actual_descriptions_and_negative_ratings(sample):
    movies, _ = sample
    model = SemanticContent(movies, document(movies), dimensions=4)
    for query in ("spaceship galaxy", "космос астронавт"):
        values = model.query_scores(query)
        assert values[:6].mean() > values[6:].mean()
    liked = model.scores({1: 5})
    disliked = model.scores({1: 1})
    assert np.allclose(liked, -disliked)
    assert model.scores({1: 3}) is None
    assert model.query_scores("unknownwordxyz") is None
    evidence = model.evidence({1: 5}, 2)
    assert evidence["seed"] == 1 and evidence["terms"]


def test_vocabulary_does_not_see_future_only_words(sample):
    movies, _ = sample
    source = document(movies)
    source["items"]["12"]["summary_en"] = "futuretokenxyz"
    model = SemanticContent(movies, source, train_ids=set(range(1, 12)), dimensions=4)
    assert "futuretokenxyz" not in model.vectorizer.vocabulary_
    assert model.query_scores("futuretokenxyz") is None


def test_identity_and_source_guards(sample):
    movies, _ = sample
    source = document(movies)
    source["items"]["1"]["original_title"] = "Unrelated film (2000)"
    source["items"]["2"]["source_url"] = "javascript:alert(1)"
    model = SemanticContent(movies, source)
    assert not model.covered[0]
    assert not model.items[2]["source_url"]
    # Native IDs in another dataset differ; matching must use title and year.
    moved = movies.copy()
    moved.movie_id += 100
    other = SemanticContent(moved, source)
    assert other.items[102]["summary_en"] == source["items"]["2"]["summary_en"]


@pytest.mark.parametrize("weights", [[float("nan"), 0, 1], [True, 0, 0], [-1, 1, 1], [0, 0, 0], "bad"])
def test_invalid_policy_is_rejected(sample, weights):
    movies, ratings = sample
    engine = Recommender(movies, ratings)
    with pytest.raises(ValueError):
        engine.attach_content(SemanticContent(engine.movies), {"3": weights})
    assert engine.semantic is None


def test_title_topic_and_temporary_feedback_are_distinct(sample):
    movies, ratings = sample
    engine = Recommender(movies, ratings)
    engine.attach_content(SemanticContent(engine.movies, document(engine.movies), dimensions=4))
    base = engine.recommend({2: 5}, "Semantic", k=12, min_ratings=0)
    title = engine.recommend({2: 5}, "Semantic", k=12, min_ratings=0, blocked={1}, topic_blocked=set())
    topic = engine.recommend({2: 5}, "Semantic", k=12, min_ratings=0, blocked={1}, topic_blocked={1})
    now = engine.recommend({2: 5}, "Semantic", k=12, min_ratings=0, snoozed={1}, topic_blocked=set())
    base_scores = {r.movie_id: r.score for r in base}
    title_scores = {r.movie_id: r.score for r in title}
    assert all(r.movie_id != 1 for r in title+topic+now)
    assert all(np.isclose(r.score, base_scores[r.movie_id]) for r in title)
    assert all(np.isclose(r.score, title_scores[r.movie_id]) for r in now)
    assert any(r.score < title_scores[r.movie_id] for r in topic)


def test_topic_export_preserves_specific_feedback_and_legacy(sample):
    engine = Recommender(*sample)
    payload = export_profile(engine, {1: 5}, {2, 3}, watched={4}, watchlist={5}, topic_blocked={2})
    assert import_library_profile(engine, payload) == ({1: 5}, {2, 3}, set(), {1, 4}, {5})
    assert import_topics(engine, payload) == {2}
    old = json.loads(payload)
    old["schema_version"] = 4
    old.pop("topic_blocked")
    assert import_topics(engine, json.dumps(old)) == {2, 3}
    old["schema_version"] = 5
    old["topic_blocked"] = [4]
    with pytest.raises(ValueError):
        import_library_profile(engine, json.dumps(old))


def test_corrupt_v3_report_is_not_accepted():
    assert not valid_v3({}, "abc")
    assert not valid_v3({"protocol_version": 3, "metadata_sha256": "old"}, "abc")
