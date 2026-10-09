import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.memory import MemoryConflict, MemoryStore, preferences
from tests.test_library import make_app


def fresh_app():
    return AppTest.from_file(str(Path(__file__).parents[1] / "app" / "streamlit_app.py"),
                             default_timeout=30).run()


def test_autosave_restores_every_signal_preferences_and_clear(dataset_dir, monkeypatch):
    app = make_app(dataset_dir, monkeypatch)
    guide = next(b for b in app.button if str(b.key).startswith("later_guide_"))
    later_id = int(guide.key.removeprefix("later_guide_"))
    guide.click().run()
    app.button(key="guide_not_seen").click().run()
    app.button(key="guide_rate_5").click().run()
    dismissed = next(b for b in app.button if str(b.key).startswith("hide_")
                     and int(b.key.removeprefix("hide_")) != later_id)
    dismissed.click().run()
    seen = next(b for b in app.button if str(b.key).startswith("seen_rec_")
                and int(b.key.removeprefix("seen_rec_")) != later_id)
    seen.click().run()
    app.button(key="seen_no_rating").click().run()
    app.selectbox(key="ui_language").set_value("uk").run()
    keys = ("ratings", "blocked", "not_seen", "watched", "watchlist")
    expected = {key: app.session_state[key] for key in keys}
    assert all(expected[key] for key in keys)
    assert later_id in expected["watchlist"]
    restored = fresh_app()
    assert not restored.exception
    assert {key: restored.session_state[key] for key in keys} == expected
    assert restored.selectbox(key="ui_language").value == "uk"
    restored.button(key="clear_profile").click().run()
    cleared = fresh_app()
    assert all(not cleared.session_state[key] for key in keys)
    assert not cleared.exception


def test_autosave_switch_demo_and_named_profiles_are_independent(dataset_dir, monkeypatch):
    app = make_app(dataset_dir, monkeypatch)
    app.button(key="guide_rate_4").click().run()
    personal = dict(app.session_state["ratings"])
    app.text_input(key="profile_name").set_value("Keep named copy").run()
    app.button(key="save_local").click().run()
    store = MemoryStore(dataset_dir / "profiles.sqlite3")
    original_named = store.load("Keep named copy")
    before_demo = store.read()
    app.button(key="demo_button").click().run()
    assert store.read() == before_demo
    assert fresh_app().session_state["ratings"] == personal
    # Disabling is persisted; a fresh session does not restore an old snapshot.
    app = fresh_app()
    app.checkbox(key="autosave").set_value(False).run()
    app.button(key="guide_rate_1").click().run()
    new_session = fresh_app()
    assert not new_session.checkbox(key="autosave").value
    assert not new_session.session_state["ratings"]
    new_session.checkbox(key="autosave").set_value(True).run()
    new_session.button(key="guide_rate_3").click().run()
    assert fresh_app().session_state["ratings"] == new_session.session_state["ratings"]
    assert store.load("Keep named copy") == original_named


def test_memory_conflict_preserves_newer_tab_and_corrupt_data(dataset_dir, monkeypatch):
    first = make_app(dataset_dir, monkeypatch)
    second = fresh_app()
    first.button(key="guide_rate_5").click().run()
    store = MemoryStore(dataset_dir / "profiles.sqlite3")
    latest = store.read()
    second.button(key="guide_rate_1").click().run()
    assert second.session_state["_memory_error"] == "memory_conflict"
    assert store.read() == latest
    assert not second.exception
    with store.connect() as connection:
        connection.execute("UPDATE current_memory SET document=? WHERE id=1", ('{broken',))
    corrupt = fresh_app()
    assert not corrupt.exception
    assert corrupt.session_state["_memory_error"] == "memory_failed"
    assert corrupt.checkbox(key="autosave").disabled
    with store.connect() as connection:
        assert connection.execute("SELECT document FROM current_memory").fetchone()[0] == '{broken'


def test_autosave_unavailable_or_disabled_keeps_app_usable(dataset_dir, monkeypatch):
    app = make_app(dataset_dir, monkeypatch)
    # The DB path is a directory: automatic and manual storage both fail neutrally.
    monkeypatch.setenv("CINEMATCH_PROFILE_DB", str(dataset_dir))
    app = fresh_app()
    assert not app.exception
    assert app.session_state["_memory_error"] == "memory_failed"
    monkeypatch.setenv("CINEMATCH_LOCAL_PROFILES", "0")
    hosted = fresh_app()
    assert not hosted.exception
    assert not any(c.key == "autosave" for c in hosted.checkbox)


def test_memory_store_cas_and_preference_whitelist(tmp_path):
    store = MemoryStore(tmp_path / "profiles.sqlite3")
    assert store.read() == (0, None)
    document = {"version": 1, "enabled": False, "profile": "", "preferences": {}}
    assert store.write(document, 0) == 1
    with pytest.raises(MemoryConflict):
        store.write(document, 0)
    assert store.read() == (1, document)
    assert preferences({"ui_language": "uk", "demo": True, "ratings": {1: 5},
                        "minimum": True, "diversity": float("nan"), "genres": [123],
                        "years": [2000, 1990], "algorithm": "pickle"}) == {"ui_language": "uk"}
    with store.connect() as connection:
        connection.execute("UPDATE current_memory SET document=?", (json.dumps({"version": 1}),))
    with pytest.raises(ValueError):
        store.read()
