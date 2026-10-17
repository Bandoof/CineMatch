"""Session isolation, default privacy and the original score formula in demo mode."""

import os
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from app.recommender import ALGORITHMS, Recommender
from src.catalog_view import CatalogView
from src.collaborative import BiasedMF
from src.data import fingerprint
from src.portfolio import (
    PACK_FILES,
    PACK_SCHEMA,
    PUBLIC_ARCHIVES,
    initial_profile,
    prepared_engine,
    reset,
    sample_catalog,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def demo(tmp_path, monkeypatch):
    monkeypatch.setenv("CINEMATCH_DEFAULT_LANGUAGE", "en")
    monkeypatch.setenv("CINEMATCH_PROFILE_DB", str(tmp_path / "must-not-be-created.sqlite3"))
    monkeypatch.setenv("CINEMATCH_PORTFOLIO_DATA_DIR", str(tmp_path / "no-public-pack"))
    monkeypatch.setenv("CINEMATCH_UI", "classic")  # Dedicated entry point must override it.
    from app import memory
    from src.profiles import ProfileStore
    from src.providers import ProviderClient

    def forbidden(*a, **k):
        raise AssertionError("Portfolio mode accessed local storage or provider credentials")

    monkeypatch.setattr(memory, "initialize", forbidden)
    monkeypatch.setattr(ProfileStore, "__init__", forbidden)
    monkeypatch.setattr(ProviderClient, "__init__", forbidden)
    return lambda: AppTest.from_file(
        str(ROOT / "app/portfolio_app.py"), default_timeout=30
    ).run(), tmp_path


def healthy(app):
    assert not app.exception
    assert not any("Temporarily unavailable" in h.value for h in app.subheader)


def test_two_sessions_changes_undo_reset_and_no_shared_storage(demo):
    make, directory = demo
    first, second = make(), make()
    healthy(first)
    healthy(second)
    first_view, second_view = (
        first.session_state["_portfolio_view"],
        second.session_state["_portfolio_view"],
    )
    assert first_view is not second_view and first_view.catalog is not second_view.catalog
    baseline = dict(second.session_state["ratings"])
    first.button_group(key="navigation_en").set_value("search").run()
    first.text_input(key="query_search").set_value("Пуститися берега").run()
    first.button(key="details_search_-169").click().run()
    first.button(key="detail_watchlist").click().run()
    assert (
        -169 in first.session_state["watchlist"] and -169 not in second.session_state["watchlist"]
    )
    first.button(key="library_undo_button").click().run()
    assert -169 not in first.session_state["watchlist"]
    first.button(key="detail_watchlist").click().run()
    first.button(key="portfolio_reset").click().run()
    assert (
        -169 not in first.session_state["watchlist"] and first.session_state["ratings"] == baseline
    )
    first.button(key="portfolio_empty").click().run()
    assert not first.session_state["ratings"] and not first.session_state["watchlist"]
    assert second.session_state["ratings"] == baseline
    assert not any(
        w.key
        in {"refresh_catalog", "refresh_details", "profile_save", "profile_load", "profile_import"}
        for w in first.button
    )
    assert not list(directory.glob("*.sqlite3"))
    fresh = make()
    healthy(fresh)
    assert fresh.session_state["ratings"] == baseline  # A new websocket session restores example.


def test_no_file_import_private_profile_controls_or_remote_queries(demo):
    make, _ = demo
    app = make()
    for page in ("search", "library", "for_you", "research", "movies", "series"):
        app.button_group(key="navigation_en").set_value(page).run()
        healthy(app)
    app.button_group(key="navigation_en").set_value("search").run()
    app.text_input(key="query_search").set_value("must stay in this visitor session").run()
    healthy(app)
    assert not any(str(b.key).startswith("remote_") for b in app.button)
    app.button_group(key="navigation_en").set_value("library").run()
    assert not app.get("file_uploader") and not any(w.key == "profile_name" for w in app.text_input)


def test_demo_controls_and_navigation_preserve_language_and_profile(demo):
    make, _ = demo
    app = make()
    baseline = dict(app.session_state["ratings"])
    assert any(e.label == "Demo mode · Details" for e in app.expander)
    app.button_group(key="navigation_en").set_value("search").run()
    app.selectbox(key="ui_language").set_value("uk").run()
    healthy(app)
    assert app.button_group(key="navigation_uk").value == "search"
    assert app.session_state["ratings"] == baseline
    assert app.button(key="portfolio_reset") and app.button(key="portfolio_empty")
    app.button(key="portfolio_empty").click().run()
    assert not app.session_state["ratings"]
    app.button(key="portfolio_reset").click().run()
    assert app.session_state["ratings"] == baseline


def test_all_sample_genres_localized_without_changing_provider_labels():
    from src.i18n import genre_name

    catalog = sample_catalog(ROOT)
    for title in catalog.titles.values():
        for genre in title.genres:
            assert genre_name(genre, "en") == genre
            assert genre_name(genre, "uk") != genre
    assert genre_name("vampire film", "uk") == "Вампірське кіно"
    assert genre_name("science fiction", "uk") == "Наукова фантастика"
    assert genre_name("DRAMA", "uk") == "Драма"
    assert genre_name("Unclassified provider genre", "uk") == "Unclassified provider genre"


def test_offline_poster_escapes_provider_text():
    def render():
        from app.product_ui import poster_fallback

        poster_fallback('<img src=x onerror="alert(1)">')

    app = AppTest.from_function(render, default_timeout=30).run()
    healthy(app)
    markup = next(m.value for m in app.markdown if "cinema-poster-fallback" in m.value)
    assert "<img" not in markup and "&lt;img" in markup


def test_reset_is_an_independent_synthetic_profile_not_movie_metadata():
    view = CatalogView(None, sample_catalog(ROOT))
    a, b = initial_profile(view), initial_profile(view)
    assert a is not b and a["ratings"] is not b["ratings"] and a["watchlist"] is not b["watchlist"]
    assert any(v <= 2 for v in a["ratings"].values()) and any(v >= 4 for v in a["ratings"].values())
    assert a["watchlist"] and a["watched"] > set(a["ratings"])
    state = {"ui_language": "uk", "_portfolio_mode": True, "library_undo": {"private": "old"}, **a}
    reset(state, view, empty=True)
    assert state["ui_language"] == "uk" and not state["ratings"] and "library_undo" not in state
    assert state["demo"] and not state["session_activity"]


def test_prepared_pack_rejects_unknown_provenance_and_symlinks(tmp_path):
    import json

    (tmp_path / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "archives": {}, "files": {}})
    )
    with pytest.raises(ValueError):
        prepared_engine(tmp_path)
    assert prepared_engine(tmp_path / "absent") is None


@pytest.fixture
def public_pack(sample, tmp_path):
    import hashlib
    import json

    movies, ratings = sample
    # Use a synthetic public-pack contract fixture, never claim it is actual live data.
    from src.catalog import canonical_catalog

    movies, ratings, _ = canonical_catalog(movies, ratings)
    movies = movies[["movie_id", "title", "year", "genres", "aliases", "media_type", "source"]]
    document = {
        "movies": json.loads(movies.to_json(orient="records")),
        "ratings": json.loads(ratings.to_json(orient="records")),
    }
    (tmp_path / "dataset.json").write_text(json.dumps(document))
    import pandas as pd

    movies, ratings = pd.DataFrame(document["movies"]), pd.DataFrame(document["ratings"])
    movies["genres"] = movies.genres.map(tuple)
    movies["aliases"] = movies.aliases.map(tuple)
    model = BiasedMF(factors=4, epochs=3).fit(ratings, movies.movie_id.to_numpy())
    model.save(tmp_path / "model.npz", fingerprint(movies, ratings))
    (tmp_path / "MOVIELENS-LICENSE.txt").write_text("Synthetic test fixture, not MovieLens data")
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": PACK_SCHEMA,
                "archives": PUBLIC_ARCHIVES,
                "files": {
                    name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
                    for name in PACK_FILES
                },
            }
        )
    )
    return tmp_path, movies, ratings, model


def test_per_visitor_cache_uses_exact_original_formula(public_pack):
    directory, movies, ratings, model = public_pack
    first, second = prepared_engine(directory), prepared_engine(directory)
    reference = Recommender(movies, ratings, collaborative=model)
    profile = {1: 5, 2: 1, 3: 4}
    expected = reference.score_components(profile)
    before = Recommender._cached_components.cache_info()
    actual = first.score_components(profile)
    for algorithm in ALGORITHMS:
        np.testing.assert_array_equal(actual[algorithm], expected[algorithm])
    assert Recommender._cached_components.cache_info() == before
    assert (
        first._cached_components.cache_info().currsize == 1
        and second._cached_components.cache_info().currsize == 0
    )


@pytest.mark.parametrize(
    "damage",
    ["old_schema", "integrity", "license", "private_field", "nan", "model_shape", "model_zip"],
)
def test_invalid_pack_is_rejected(public_pack, damage):
    import hashlib
    import json

    directory, _, _, _ = public_pack
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if damage == "old_schema":
        manifest["schema_version"] = 1
    elif damage == "integrity":
        (directory / "dataset.json").write_text("{}")
    elif damage == "license":
        (directory / "MOVIELENS-LICENSE.txt").unlink()
    elif damage in {"private_field", "nan"}:
        path = directory / "dataset.json"
        document = json.loads(path.read_text())
        if damage == "private_field":
            document["ratings"][0]["email"] = "not-a-real-address"
        else:
            document["ratings"][0]["rating"] = float("nan")
        path.write_text(json.dumps(document))
        manifest["files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    else:
        path = directory / "model.npz"
        if damage == "model_zip":
            path.write_bytes(b"not a zip")
        else:
            with np.load(path, allow_pickle=False) as archive:
                arrays = {name: archive[name] for name in archive.files}
            arrays["item_factors"] = np.zeros((1, 4))
            np.savez_compressed(path, **arrays)
        manifest["files"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        prepared_engine(directory)


def test_invalid_pack_falls_back_visibly(demo, public_pack, monkeypatch):
    make, _ = demo
    directory, _, _, _ = public_pack
    (directory / "dataset.json").write_text("{}")
    monkeypatch.setenv("CINEMATCH_PORTFOLIO_DATA_DIR", str(directory))
    app = make()
    healthy(app)
    assert app.session_state["_portfolio_pack_error"]
    assert app.session_state["_portfolio_view"].base is None
    assert app.warning


@pytest.mark.skipif(
    not os.environ.get("CINEMATCH_TEST_PUBLIC_PACK"), reason="Explicit real pack required"
)
def test_real_pack_rating_changes_ml_only_in_visitor_session(demo, monkeypatch):
    make, _ = demo
    monkeypatch.setenv("CINEMATCH_PORTFOLIO_DATA_DIR", os.environ["CINEMATCH_TEST_PUBLIC_PACK"])
    first, second = make(), make()
    healthy(first)
    healthy(second)
    first_view = first.session_state["_portfolio_view"]
    second_view = second.session_state["_portfolio_view"]
    assert first_view.base is not None and second_view.base is not None
    assert not first_view.base.has_learned_policy and first_view.base.semantic is None
    baseline_profile = dict(second.session_state["ratings"])
    assert baseline_profile and any(r <= 2 for r in baseline_profile.values())
    baseline_scores = second_view.base.score_components(second_view.known_profile(baseline_profile))
    first.button(key="portfolio_empty").click().run()
    first.button_group(key="navigation_en").set_value("for_you").run()
    assert first.selectbox(key="for_you_algorithm").value == "Collaborative"
    assert any("Rate at least one" in item.value for item in first.info)
    before = first_view.base.score_components({})["Collaborative"]
    first.button_group(key="navigation_en").set_value("search").run()
    first.text_input(key="query_search").set_value("Star Wars (1977)").run()
    mid = next(
        int(row.movie_id)
        for row in first_view.base.movies.itertuples()
        if row.imdb_id == "tt0076759"
    )
    first.button(key=f"details_search_{mid}").click().run()
    first.select_slider(key=f"stars_{mid}").set_value(4.5)
    next(b for b in first.button if b.label == "Save rating").click().run()
    healthy(first)
    assert first.session_state["ratings"] == {mid: 4.5}
    after = first_view.base.score_components({mid: 4.5})["Collaborative"]
    assert np.isfinite(after).all() and not np.allclose(before, after)
    original = Recommender(
        first_view.base.movies, first_view.base.ratings, collaborative=first_view.base.collaborative
    )
    np.testing.assert_array_equal(after, original.score_components({mid: 4.5})["Collaborative"])
    first.button_group(key="navigation_en").set_value("for_you").run()
    healthy(first)
    assert not any("Rate at least one" in item.value for item in first.info)
    assert second.session_state["ratings"] == baseline_profile
    for name, scores in baseline_scores.items():
        np.testing.assert_array_equal(
            scores,
            second_view.base.score_components(second_view.known_profile(baseline_profile))[name],
        )
    first.button(key="portfolio_reset").click().run()
    assert first.session_state["ratings"] == baseline_profile
    # Synthetic examples are resolved by IMDb identity in the latest-small namespace.
    assert all(mid >= 1_000_000 for mid in first_view.known_profile(baseline_profile))


def test_prepare_refuses_existing_destination_and_changed_source(tmp_path, monkeypatch):
    import json

    from scripts import prepare_portfolio

    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "owner-file.txt"
    marker.write_text("preserve")
    with pytest.raises(ValueError, match="Destination exists"):
        prepare_portfolio.prepare(existing)
    assert marker.read_text() == "preserve"

    def changed_source(directory):
        directory.mkdir()
        (directory / "source.json").write_text(json.dumps({"archive_sha256": "changed"}))

    monkeypatch.setattr(prepare_portfolio, "download_latest", changed_source)
    destination = tmp_path / "new-pack"
    with pytest.raises(ValueError, match="archive changed"):
        prepare_portfolio.prepare(destination)
    assert not destination.exists()
    assert not list(tmp_path.glob("cinematch-public-pack-*"))
