import json
import hashlib
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

from app.recommender import Recommender
from scripts.benchmark_v3 import targets
from src.discovery import discovery_queue
from src.semantic import SemanticContent
from src.data import fingerprint, load_app_movies


def test_recognition_exploration_preserves_neutral_skips(sample):
    engine = Recommender(*sample)
    engine.attach_content(SemanticContent(engine.movies, dimensions=4))
    profile = {1: 5, 2: 4, 3: 1}
    before = engine.score_components(profile)
    queue = discovery_queue(engine, profile, not_seen={4}, blocked={5}, watched={6})
    assert len(queue) == len(set(queue)) == 6
    assert not {1, 2, 3, 4, 5, 6} & set(queue)
    assert 4 in {r.movie_id for r in engine.recommend(profile, k=12)}
    for name, values in before.items():
        assert np.array_equal(values, engine.score_components(profile)[name])


def test_target_selection_is_deterministic_and_removes_previous_positives(sample):
    _, ratings = sample
    past = ratings.copy()
    future = ratings.copy()
    future.movie_id += 100
    first = targets(past, future, 5)
    second = targets(past.sample(frac=1, random_state=2), future.sample(frac=1, random_state=3), 5)
    assert len(first) == 5
    assert [row[0] for row in first] == [row[0] for row in second]
    assert all(not set(history.movie_id) & relevant for _, history, relevant in first)


def test_ui_feedback_modes_undo_and_automatic_restore(dataset_dir, monkeypatch):
    for key, value in {"CINEMATCH_DATA_DIR": dataset_dir, "CINEMATCH_ARTIFACT_ROOT": dataset_dir,
                       "CINEMATCH_SERIES_FILE": dataset_dir / "missing.json",
                       "CINEMATCH_METADATA_FILE": dataset_dir / "missing-metadata.json",
                       "CINEMATCH_PROFILE_DB": dataset_dir / "profile.sqlite3",
                       "CINEMATCH_DEFAULT_LANGUAGE": "en"}.items():
        monkeypatch.setenv(key, str(value))
    entry = str(Path(__file__).parents[1] / "app/streamlit_app.py")
    app = AppTest.from_file(entry, default_timeout=30).run()
    assert not app.exception
    assert [t.label for t in app.tabs if t.label in ("For you", "My library", "ML Lab")] == ["For you", "My library", "ML Lab"]
    app.radio(key="interest_mode").set_value("title").run()
    button = next(b for b in app.button if b.key and b.key.startswith("hide_"))
    mid = int(button.key[5:])
    button.click().run()
    assert mid in app.session_state["blocked"] and not app.session_state["topic_blocked"]
    reopened = AppTest.from_file(entry, default_timeout=30).run()
    assert mid in reopened.session_state["blocked"] and not reopened.session_state["topic_blocked"]
    # Continue the newer session; concurrent sessions deliberately cannot overwrite.
    reopened.button(key="restore_hidden").click().run()
    reopened.radio(key="interest_mode").set_value("now").run()
    button = next(b for b in reopened.button if b.key and b.key.startswith("hide_"))
    mid = int(button.key[5:])
    button.click().run()
    assert mid in reopened.session_state["snoozed"] and not reopened.session_state["blocked"]
    reopened.button(key="interest_undo").click().run()
    assert not reopened.session_state["snoozed"]
    reopened.button(key="guide_rate_5").click().run()
    assert "recommendation_change" in reopened.session_state
    assert any("New titles in Top-10" in t.value for t in reopened.caption)
    reopened.radio(key="interest_mode").set_value("topic").run()
    next(b for b in reopened.button if b.key and b.key.startswith("hide_")).click().run()
    assert reopened.session_state["topic_blocked"] == reopened.session_state["blocked"]
    doc = json.loads(reopened.session_state["_memory_document"]["profile"])
    assert doc["topic_blocked"] == sorted(reopened.session_state["topic_blocked"])
    assert "snoozed" not in doc
    assert not reopened.exception


def test_lab_renders_current_and_archived_artifacts_without_public_error(dataset_dir, monkeypatch):
    for key, value in {"CINEMATCH_DATA_DIR": dataset_dir, "CINEMATCH_ARTIFACT_ROOT": dataset_dir,
                       "CINEMATCH_SERIES_FILE": dataset_dir / "missing.json",
                       "CINEMATCH_METADATA_FILE": dataset_dir / "missing.json",
                       "CINEMATCH_CONTENT_FILE": dataset_dir / "content.json",
                       "CINEMATCH_PROFILE_DB": dataset_dir / "profiles.sqlite3",
                       "CINEMATCH_DEFAULT_LANGUAGE": "en"}.items():
        monkeypatch.setenv(key, str(value))
    # Synthetic artifact fixtures exercise paths absent from a fresh empty app.
    movies, ratings = load_app_movies(dataset_dir)
    content = {"schema_version": 1, "items": {}}
    encoded = json.dumps(content).encode()
    (dataset_dir / "content.json").write_bytes(encoded)
    reports = dataset_dir / "reports"
    reports.mkdir()
    names = ("Hybrid", "Collaborative", "Item-KNN", "Content-based", "Popularity")
    metrics = {k: .1 for k in ("precision@10", "recall@10", "ndcg@10", "coverage", "diversity")}
    archive = {"fingerprint": fingerprint(movies, ratings), "protocol_version": 2, "selected_alpha": .75,
               "metrics": {name: metrics for name in names},
               "confidence_95": {name: {"ndcg@10": [.05, .15]} for name in names},
               "test_cohort": {"evaluated_users": 12}, "onboarding": {"results": []}, "diversity_analysis": []}
    (reports / "metrics.json").write_text(json.dumps(archive))
    current = {"protocol_version": 3, "dataset": "MovieLens 1M", "metadata_sha256": hashlib.sha256(encoded).hexdigest(),
               "test_users": 12, "validation_users": 12, "events": 120,
               "selected_policy": {str(n): [.25, .25, .5] for n in (3, 5, 10)},
               "results": [{"seed_ratings": n, "algorithm": name, **metrics, "ndcg@10": n/100} for n in (3, 5, 10)
                           for name in ("Popularity", "Collaborative", "Semantic", "Genres", "Adaptive")],
               "paired_ndcg_vs_popularity_95": {str(n): {"Adaptive": [-.01, .01]} for n in (3, 5, 10)}}
    (reports / "ml_v3.json").write_text(json.dumps(current))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app/streamlit_app.py"), default_timeout=30).run()
    assert not app.exception
    assert any(tab.label == "Archived film benchmark" for tab in app.tabs)
    assert any("120 rating events" in text.value for text in app.caption)
    assert any("Five approaches" in text.value for text in app.subheader)
    assert not any(button.key == "service_retry" for button in app.button)
    assert (app.dataframe[0].value["ndcg@10"] == .05).all()
    app.radio(key="ml_seeds").set_value(3).run()
    assert (app.dataframe[0].value["ndcg@10"] == .03).all()
    app.selectbox(key="ui_language").set_value("uk").run()
    assert not any(button.key == "service_retry" for button in app.button)
