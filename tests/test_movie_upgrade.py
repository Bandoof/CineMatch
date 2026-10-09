import json

import numpy as np
import pandas as pd
from scipy.sparse import issparse

from app.recommender import ALGORITHMS, Recommender
from src.item_knn import ItemKNN
from src.metadata import CatalogMetadata
from src.movies import extend_movies
from src.profiles import export_profile, import_library_profile
from src.search import identity_keys, title_matches
from src.series import parse_show
from tests.test_library import make_app


def test_extended_catalog_preserves_old_ids_aliases_real_ratings_and_user_namespaces(sample, tmp_path):
    movies, ratings = sample
    movies = movies.copy()
    movies.loc[0, "title"] = "Professional, The (1994)"
    movies.loc[0, "year"] = 1994
    movies["aliases"] = [(mid,) for mid in movies.movie_id]
    latest = pd.DataFrame({"movieId": [110, 58559, 109487, 92259], "title": [
        "Léon: The Professional (a.k.a. The Professional) (Léon) (1994)",
        "Dark Knight, The (2008)", "Interstellar (2014)", "Intouchables (2011)"],
        "genres": ["Crime|Drama|Thriller", "Action|Crime|Drama", "Adventure|Sci-Fi", "Comedy|Drama"]})
    latest.to_csv(tmp_path / "movies.csv", index=False)
    pd.DataFrame({"movieId": latest.movieId, "imdbId": [110413, 468569, 816692, 1675434]}).to_csv(
        tmp_path / "links.csv", index=False)
    pd.DataFrame({"userId": [1, 1, 2, 3], "movieId": latest.movieId,
                  "rating": [.5, 5, 4.5, 4], "timestamp": [1000, 1001, 1002, 1003]}).to_csv(
        tmp_path / "ratings.csv", index=False)
    extended, observations = extend_movies(movies, ratings, tmp_path)
    assert len(extended) == len(movies) + 3
    assert set(movies.movie_id) <= set(extended.movie_id)
    assert 1_000_110 in extended.loc[extended.movie_id.eq(1), "aliases"].iloc[0]
    actual = observations.tail(4)
    assert actual.movie_id.tolist() == [1, 1_058_559, 1_109_487, 1_092_259]
    assert actual.user_id.tolist() == [1_000_001, 1_000_001, 1_000_002, 1_000_003]
    assert actual.rating.tolist() == [.5, 5, 4.5, 4]
    engine = Recommender(extended, observations)
    old_json = '{"1":5}'
    assert import_library_profile(engine, old_json)[0] == {1: 5}
    assert engine.validate_profile({1_000_110: .5}) == {1: .5}
    saved = export_profile(engine, {1: 5}, set(), watchlist={1_109_487})
    assert import_library_profile(engine, saved)[4] == {1_109_487}


def test_search_accents_punctuation_ukrainian_aliases_and_remake_identity():
    assert title_matches("Leon", "Léon (1994)")
    assert title_matches("Léon", "Professional, The (1994)", "Léon")
    assert title_matches("1+1", "Недоторканні", "1 + 1")
    assert not title_matches("1+1", "Босий керівник (фільм, 1971) (1971)")
    assert title_matches("ІНТЕРСТЕЛЛАР", "Інтерстеллар (2014)")
    assert not title_matches("Матриця", "Інтерстеллар (2014)")
    assert not title_matches("nan", np.nan, None)
    assert not identity_keys("The Thing (1982)") & identity_keys("Thing, The (2011)")
    assert identity_keys("Léon: The Professional (a.k.a. The Professional) (Léon) (1994)") & identity_keys("Professional, The (1994)")


def test_sparse_knn_matches_dense_adjusted_cosine_and_has_no_quadratic_storage(sample):
    movies, ratings = sample
    users = {uid: i for i, uid in enumerate(sorted(ratings.user_id.unique()))}
    matrix = np.zeros((len(users), len(movies)))
    mask = np.zeros_like(matrix)
    for row in ratings.itertuples():
        matrix[users[row.user_id], row.movie_id - 1] = row.rating
        mask[users[row.user_id], row.movie_id - 1] = 1
    means = matrix.sum(axis=1) / mask.sum(axis=1)
    centered = (matrix - means[:, None]) * mask
    norms = np.linalg.norm(centered, axis=0)
    denominator = norms[:, None] * norms[None, :]
    weights = np.divide(centered.T @ centered, denominator, out=np.zeros_like(denominator), where=denominator > 0)
    common = mask.T @ mask
    weights = np.maximum(weights * common / (common + 10), 0)
    np.fill_diagonal(weights, 0)
    profile = {1: 5, 2: 1, 8: 4, 10: 2}
    indices = np.array(list(profile)) - 1
    values = np.array(list(profile.values()))
    selected = weights[:, indices]
    selected[np.arange(len(movies))[:, None], np.argsort(-selected, axis=1)[:, 2:]] = 0
    fallback = np.full(len(movies), 3.5)
    expected = np.divide(selected @ (values - values.mean()), selected.sum(axis=1),
                         out=fallback.copy() - values.mean(), where=selected.sum(axis=1) > 0) + values.mean()
    model = ItemKNN(neighbors=2).fit(ratings, movies.movie_id)
    np.testing.assert_allclose(model.scores(profile, fallback), expected, atol=1e-12)
    large = ItemKNN().fit(ratings, np.arange(1, 10_001))
    assert issparse(large.centered) and large.centered.nnz == len(ratings)
    assert not hasattr(large, "similarity")
    assert large.centered.data.nbytes + large.mask.data.nbytes < 100_000


def test_not_interested_lowers_similar_genres_without_creating_ratings(sample):
    engine = Recommender(*sample)
    for algorithm in ALGORITHMS:
        before = {row.movie_id: row.score for row in engine.recommend({}, algorithm, k=20)}
        after = {row.movie_id: row.score for row in engine.recommend({}, algorithm, k=20, blocked={1})}
        assert 1 not in after
        assert after[2] < before[2]
        assert after[8] == before[8]
        restored = {row.movie_id: row.score for row in engine.recommend({}, algorithm, k=20, blocked=set())}
        assert before == restored
    document = json.loads(export_profile(engine, {}, {1}))
    assert document["ratings"] == [] and document["watched"] == []


def test_mixed_results_are_balanced_and_short_lists_fill_available_type(sample):
    series = pd.DataFrame([parse_show({"id": mid, "name": f"Show {mid}", "type": "Scripted",
        "premiered": "2008-01-20", "genres": ["Drama"], "rating": {"average": 9.9},
        "url": f"https://www.tvmaze.com/shows/{mid}/show"}) for mid in range(1, 13)])
    engine = Recommender(*sample, series=series)
    all_results = engine.recommend({})
    assert sum(row.media_type == "Movie" for row in all_results) == 5
    assert sum(row.media_type == "Series" for row in all_results) == 5
    assert engine.recommend({}, k=1)[0].media_type == "Movie"
    only_one_show = engine.recommend({}, k=10, blocked=set(range(-12, -1)))
    assert len(only_one_show) == 10
    assert sum(row.media_type == "Series" for row in only_one_show) == 1


def test_not_interested_ui_undo_and_individual_restore(dataset_dir, monkeypatch):
    app = make_app(dataset_dir, monkeypatch)
    later = next(button for button in app.button if str(button.key).startswith("later_rec_"))
    mid = int(later.key.removeprefix("later_rec_"))
    later.click().run()
    app.button(key=f"hide_{mid}").click().run()
    assert app.session_state["blocked"] == {mid}
    assert not app.session_state["watchlist"] and not app.session_state["ratings"]
    app.button(key="interest_undo").click().run()
    assert not app.session_state["blocked"] and app.session_state["watchlist"] == {mid}
    app.button(key=f"hide_{mid}").click().run()
    app.button(key=f"restore_interest_{mid}").click().run()
    assert not app.session_state["blocked"] and not app.exception


def test_metadata_aliases_are_presentation_only(sample):
    engine = Recommender(*sample)
    before = engine.score_components({1: 5})["Hybrid"].copy()
    document = {"schema_version": 1, "items": {"1": {"original_title": engine.movies.iloc[0].title,
        "title_uk": "Леон", "search_aliases": ["Léon", "Леон-кілер"]}}}
    engine.metadata = CatalogMetadata(engine.movies, document)
    assert "Léon" in engine.metadata.items[1]["search_aliases"]
    np.testing.assert_array_equal(before, engine.score_components({1: 5})["Hybrid"])


def test_profile_scoring_cache_is_reused_but_cannot_be_mutated(sample, monkeypatch):
    engine = Recommender(*sample)
    calls = []
    original = engine.knn.scores

    def record_call(profile, fallback):
        calls.append(profile.copy())
        return original(profile, fallback)

    monkeypatch.setattr(engine.knn, "scores", record_call)
    first = engine.score_components({1: 5})
    expected = first["Hybrid"].copy()
    first["Hybrid"][:] = -999
    np.testing.assert_array_equal(engine.score_components({1: 5})["Hybrid"], expected)
    engine.recommend({1: 5}, blocked={2})
    assert len(calls) == 1
    engine.score_components({1: 1})
    assert len(calls) == 2
    engine.alpha = 0
    assert not np.array_equal(expected, engine.score_components({1: 5})["Hybrid"])
    assert len(calls) == 3
