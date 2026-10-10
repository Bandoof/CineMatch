"""Session isolation, default privacy and the original score formula in demo mode."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from app.recommender import ALGORITHMS, Recommender
from src.catalog_view import CatalogView
from src.collaborative import BiasedMF
from src.data import fingerprint
from src.portfolio import PUBLIC_ARCHIVES, initial_profile, prepared_engine, reset, sample_catalog

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
    first.radio(key="navigation_en").set_value("search").run()
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
        app.radio(key="navigation_en").set_value(page).run()
        healthy(app)
    app.radio(key="navigation_en").set_value("search").run()
    app.text_input(key="query_search").set_value("must stay in this visitor session").run()
    healthy(app)
    assert not any(str(b.key).startswith("remote_") for b in app.button)
    app.radio(key="navigation_en").set_value("library").run()
    assert not app.get("file_uploader") and not any(w.key == "profile_name" for w in app.text_input)


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


def test_per_visitor_cache_uses_exact_original_formula(sample, tmp_path):
    import hashlib
    import json

    movies, ratings = sample
    # Use a synthetic public-pack contract fixture, never claim it is actual live data.
    from src.catalog import canonical_catalog

    movies, ratings, _ = canonical_catalog(movies, ratings)
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
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "archives": PUBLIC_ARCHIVES,
                "files": {
                    name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
                    for name in ("dataset.json", "model.npz")
                },
            }
        )
    )
    first, second = prepared_engine(tmp_path), prepared_engine(tmp_path)
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
