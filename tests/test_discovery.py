import json
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

from app.recommender import Recommender
from src.discovery import discovery_queue
from src.metadata import CatalogMetadata
from src.profiles import export_profile, import_discovery_profile


def test_localized_titles_keep_identity_scores_and_reject_wrong_remakes(sample):
    engine = Recommender(*sample)
    before = engine.score_components({1: 5})
    engine.metadata = CatalogMetadata(engine.movies, {"schema_version": 1, "items": {
        "1": {"original_title": "Test film 1 (1995)", "title_uk": "Перший фільм",
              "poster_url": "https://upload.wikimedia.org/wikipedia/en/example.jpg"},
        "2": {"original_title": "Test film 2 (2025)", "title_uk": "Wrong remake"},
        "3": {"original_title": "Test film 3 (1995)", "title_uk": "Третій фільм (1995)",
              "poster_url": "https://malicious.example/track"}}})
    assert engine.display_title(1, "uk") == "Перший фільм (1995)"
    assert engine.display_title(1, "en") == "Test film 1 (1995)"
    assert engine.display_title(3, "uk") == "Третій фільм (1995)"
    engine.metadata.items[3]["title_uk"] = "Третій фільм (фільм, 1995)"
    assert engine.display_title(3, "uk") == "Третій фільм (1995)"
    engine.metadata.items[2] = {"title_uk": "Test film 2"}
    assert not engine.metadata.translated(2)
    engine.metadata.items[2] = {"title_uk": "1+1"}
    assert engine.metadata.translated(2)
    engine.metadata.items.pop(2)
    assert not engine.metadata.translated(2)
    assert engine.metadata.items[3]["poster_url"] == ""
    for model, scores in before.items():
        np.testing.assert_array_equal(engine.score_components({1: 5})[model], scores)
    results = engine.recommend({1: 5}, language="uk", localized_only=True)
    assert {row.movie_id for row in results} == {3}
    assert "Перший фільм" in results[0].reason


def test_not_seen_is_not_a_dislike_and_profiles_are_backwards_compatible(sample):
    engine = Recommender(*sample)
    initial = discovery_queue(engine)
    skipped = initial[0]
    queue = discovery_queue(engine, {initial[1]: 5}, {skipped}, {initial[2]})
    assert len(queue) == len(set(queue)) == len(engine.movie_ids) - 3
    assert not {skipped, initial[1], initial[2]} & set(queue)
    # A skipped title is still eligible for actual recommendations.
    assert skipped in {row.movie_id for row in engine.recommend(k=12)}
    payload = export_profile(engine, {initial[1]: 5}, {initial[2]}, {skipped})
    assert import_discovery_profile(engine, payload) == ({initial[1]: 5}, {initial[2]}, {skipped})
    document = json.loads(payload)
    document["schema_version"] = 2
    document.pop("not_seen")
    assert import_discovery_profile(engine, json.dumps(document))[2] == set()


def test_guided_rate_skip_undo_and_reload(dataset_dir, monkeypatch):
    for key, value in {"CINEMATCH_DATA_DIR": dataset_dir, "CINEMATCH_ARTIFACT_ROOT": dataset_dir,
                       "CINEMATCH_SERIES_FILE": dataset_dir / "missing.json",
                       "CINEMATCH_METADATA_FILE": dataset_dir / "missing-metadata.json",
                       "CINEMATCH_PROFILE_DB": dataset_dir / "profile.sqlite3",
                       "CINEMATCH_DEFAULT_LANGUAGE": "en"}.items():
        monkeypatch.setenv(key, str(value))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app" / "streamlit_app.py")).run()
    first_title = app.subheader[0].value
    app.button(key="guide_not_seen").click().run()
    assert not app.exception and not app.session_state["ratings"]
    assert len(app.session_state["not_seen"]) == 1
    assert app.subheader[0].value != first_title
    app.button(key="guide_undo").click().run()
    assert not app.session_state["not_seen"]
    assert app.subheader[0].value == first_title
    app.button(key="guide_rate_5").click().run()
    assert len(app.session_state["ratings"]) == 1
    assert not app.session_state["not_seen"]
    app.button(key="guide_not_seen").click().run()
    expected = (dict(app.session_state["ratings"]), set(app.session_state["not_seen"]))
    app.text_input(key="profile_name").set_value("Recognition test").run()
    app.button(key="save_local").click().run()
    app.button(key="clear_profile").click().run()
    app.button(key="load_local").click().run()
    assert (app.session_state["ratings"], app.session_state["not_seen"]) == expected
    assert not app.exception
