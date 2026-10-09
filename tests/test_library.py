import json
import sqlite3
from pathlib import Path

import pandas as pd
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from app.recommender import ALGORITHMS, Recommender
from src.discovery import discovery_queue
from src.profiles import ProfileStore, export_profile, import_library_profile
from src.series import parse_show


def make_app(dataset_dir, monkeypatch, language="en"):
    for key, value in {"CINEMATCH_DATA_DIR": dataset_dir, "CINEMATCH_ARTIFACT_ROOT": dataset_dir,
                       "CINEMATCH_SERIES_FILE": dataset_dir / "absent-series.json",
                       "CINEMATCH_METADATA_FILE": dataset_dir / "absent-metadata.json",
                       "CINEMATCH_PROFILE_DB": dataset_dir / "profiles.sqlite3",
                       "CINEMATCH_DEFAULT_LANGUAGE": language}.items():
        monkeypatch.setenv(key, str(value))
    return AppTest.from_file(str(Path(__file__).parents[1] / "app" / "streamlit_app.py"),
                             default_timeout=30).run()


def test_watched_aliases_and_series_excluded_without_creating_ratings(sample):
    movies, ratings = sample
    movies = movies.copy()
    movies["imdb_url"] = [f"https://example.com/{mid}" for mid in movies.movie_id]
    alias = movies.iloc[0].copy()
    alias.movie_id = 13
    movies = pd.concat([movies, alias.to_frame().T], ignore_index=True)
    series = pd.DataFrame([parse_show({"id": 169, "name": "Breaking Bad", "type": "Scripted",
        "premiered": "2008-01-20", "genres": ["Drama"], "rating": {"average": 9.2},
        "url": "https://www.tvmaze.com/shows/169/breaking-bad"})])
    engine = Recommender(movies, ratings, series=series)
    for model in ALGORITHMS:
        results = engine.recommend({}, model, k=20, watched={13, -169})
        assert not {1, 13, -169} & {row.movie_id for row in results}
    assert not {1, -169} & set(discovery_queue(engine, watched={13, -169}))
    assert engine.validate_profile({}) == {}
    restored = engine.recommend({}, k=20)
    assert {1, -169} <= {row.movie_id for row in restored}


def test_library_profiles_roundtrip_validation_and_old_versions(sample):
    engine = Recommender(*sample)
    payload = export_profile(engine, {1: 4}, {5}, {4, 2}, {2}, {3, 1})
    assert import_library_profile(engine, payload) == ({1: 4}, {5}, {4}, {1, 2}, {3})
    for field, value in (("watched", [True]), ("watchlist", [99999]), ("watchlist", {"3": True})):
        invalid = json.loads(payload)
        invalid[field] = value
        with pytest.raises(ValueError):
            import_library_profile(engine, json.dumps(invalid))
    for version in (2, 3):
        old = {"schema_version": version, "app": "CineMatch", "ratings": [{"item_id": 1, "rating": 5}],
               "blocked": [], "not_seen": [2]}
        restored = import_library_profile(engine, json.dumps(old))
        assert restored[3:] == ({1}, set())
        assert restored[2] == ({2} if version == 3 else set())
    assert import_library_profile(engine, '{"1":5}')[3:] == ({1}, set())


def test_watch_later_seen_optional_rating_undo_and_persistence(dataset_dir, monkeypatch):
    app = make_app(dataset_dir, monkeypatch)
    guide_button = next(button for button in app.button if str(button.key).startswith("later_guide_"))
    guide_id = int(guide_button.key.removeprefix("later_guide_"))
    guide_button.click().run()
    assert app.session_state["watchlist"] == {guide_id}
    assert not app.session_state["ratings"] and not app.session_state["watched"]
    app.button(key="guide_rate_5").click().run()
    assert not app.session_state["watchlist"] and guide_id in app.session_state["watched"]
    app.button(key="guide_undo").click().run()
    assert app.session_state["watchlist"] == {guide_id}
    assert not app.session_state["ratings"] and not app.session_state["watched"]
    rec_button = next(button for button in app.button
                      if str(button.key).startswith("later_rec_") and int(button.key[10:]) != guide_id)
    rec_id = int(rec_button.key.removeprefix("later_rec_"))
    rec_button.click().run()
    assert app.session_state["watchlist"] == {guide_id, rec_id}
    app.button(key=f"seen_rec_{rec_id}").click().run()
    assert rec_id in app.session_state["watched"] and rec_id not in app.session_state["watchlist"]
    assert not app.session_state["ratings"]
    app.button(key="seen_cancel").click().run()
    assert rec_id in app.session_state["watchlist"] and rec_id not in app.session_state["watched"]
    app.button(key=f"seen_rec_{rec_id}").click().run()
    app.button(key="seen_no_rating").click().run()
    assert rec_id in app.session_state["watched"] and not app.session_state["ratings"]
    assert not any(button.key == f"seen_rec_{rec_id}" for button in app.button)
    app.text_input(key="profile_name").set_value("Watch later test").run()
    app.button(key="save_local").click().run()
    app.button(key="clear_profile").click().run()
    app.button(key="load_local").click().run()
    assert app.session_state["watchlist"] == {guide_id}
    assert app.session_state["watched"] == {rec_id}
    app.button(key=f"restore_seen_{rec_id}").click().run()
    assert not app.session_state["watched"]
    app.button(key=f"seen_later_{guide_id}").click().run()
    app.button(key=f"seen_rate_{guide_id}_4").click().run()
    assert app.session_state["ratings"] == {guide_id: 4}
    assert app.session_state["watched"] == {guide_id}
    assert not app.session_state["watchlist"] and not app.exception


def test_ukrainian_without_metadata_keeps_catalog_usable(dataset_dir, monkeypatch):
    app = make_app(dataset_dir, monkeypatch, "uk")
    assert not app.exception
    assert not app.checkbox(key="localized_only").value
    assert any(str(button.key).startswith("later_guide_") for button in app.button)
    assert any(str(button.key).startswith("later_rec_") for button in app.button)


def test_sqlite_connections_close_and_failed_transactions_rollback(tmp_path):
    store = ProfileStore(tmp_path / "profiles.sqlite3")
    with store.connect() as connection:
        connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    with pytest.raises(RuntimeError), store.connect() as transaction:
        transaction.execute("INSERT INTO profiles(name,payload) VALUES ('temporary','{}')")
        raise RuntimeError("Simulated failure")
    assert store.names() == []


def test_series_only_history_personalizes_hybrid_films_at_validated_alpha(sample):
    series = pd.DataFrame([parse_show({"id": 169, "name": "Test science fiction", "type": "Scripted",
        "premiered": "2008-01-20", "genres": ["Science-Fiction"], "rating": {"average": 9.2},
        "url": "https://www.tvmaze.com/shows/169/test"})])
    engine = Recommender(*sample, series=series, alpha=1.0)
    liked = engine.recommend({-169: 5}, media_type="Movie", algorithm="Hybrid")
    disliked = engine.recommend({-169: 1}, media_type="Movie", algorithm="Hybrid")
    assert "Sci-Fi" in liked[0].genres
    assert "Sci-Fi" not in disliked[0].genres
    assert "no movie rating history" in liked[0].reason
    # Film-rated profiles retain the benchmark's original formula exactly.
    components = engine.score_components({1: 5})
    np.testing.assert_allclose(components["Hybrid"][:engine.film_count],
        (np.clip(components["Collaborative"][:engine.film_count], 1, 5) - 1) / 4)
