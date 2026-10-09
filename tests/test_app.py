from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_rating_hide_and_restore_workflow(dataset_dir, monkeypatch):
    monkeypatch.setenv("CINEMATCH_DATA_DIR", str(dataset_dir))
    monkeypatch.setenv("CINEMATCH_DEFAULT_LANGUAGE", "en")
    monkeypatch.setenv("CINEMATCH_ARTIFACT_ROOT", str(dataset_dir))
    monkeypatch.setenv("CINEMATCH_SERIES_FILE", str(dataset_dir / "absent.json"))
    monkeypatch.setenv("CINEMATCH_METADATA_FILE", str(dataset_dir / "absent-metadata.json"))
    monkeypatch.setenv("CINEMATCH_PROFILE_DB", str(dataset_dir / "profiles.sqlite3"))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app" / "streamlit_app.py"))
    app.run(timeout=30)
    assert not app.exception
    app.button(key="FormSubmitter:rate_movie-Save rating").click().run()
    assert not app.exception
    assert len(app.session_state["ratings"]) == 1
    hide = next(b for b in app.button if b.label == "Not interested")
    hide.click().run()
    assert not app.exception
    assert len(app.session_state["blocked"]) == 1
    app.button(key="restore_hidden").click().run()
    assert not app.exception
    assert not app.session_state["blocked"]
    app.button(key="clear_profile").click().run()
    assert not app.exception
    assert not app.session_state["ratings"]


def test_ukrainian_series_and_saved_profile(dataset_dir, monkeypatch):
    import json

    from src.i18n import tr

    series_file = dataset_dir / "series.json"
    metadata_file = dataset_dir / "metadata.json"
    metadata_file.write_text(json.dumps({"schema_version": 1, "items": {
        "-169": {"original_title": "Breaking Bad (2008)", "title_uk": "Пуститися берега",
                 "title_source": "https://www.wikidata.org/wiki/Q1079"}}}), encoding="utf-8")
    series_file.write_text(json.dumps({"schema_version": 1, "source": "TVmaze",
        "shows": [{"id": 169, "name": "Breaking Bad", "type": "Scripted",
                   "premiered": "2008-01-20", "genres": ["Drama", "Crime"],
                   "rating": {"average": 9.2}, "url": "https://www.tvmaze.com/shows/169/breaking-bad"}]}),
        encoding="utf-8")
    for key, value in {"CINEMATCH_DATA_DIR": dataset_dir,
                       "CINEMATCH_ARTIFACT_ROOT": dataset_dir,
                       "CINEMATCH_SERIES_FILE": series_file,
                       "CINEMATCH_METADATA_FILE": metadata_file,
                       "CINEMATCH_PROFILE_DB": dataset_dir / "profiles.sqlite3",
                       "CINEMATCH_DEFAULT_LANGUAGE": "uk"}.items():
        monkeypatch.setenv(key, str(value))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app" / "streamlit_app.py")).run()
    assert not app.exception
    assert app.tabs[0].label == tr("for_you", "uk")
    app.selectbox(key="media_type").set_value("Series").run()
    assert not app.exception
    assert any("Пуститися берега" in text.value for text in app.subheader)
    app.button(key="FormSubmitter:rate_movie-" + tr("save_rating", "uk")).click().run()
    assert app.session_state["ratings"] == {-169: 4}
    app.text_input(key="profile_name").set_value("Мій профіль").run()
    app.button(key="save_local").click().run()
    assert any(text.value == tr("saved_ok", "uk") for text in app.success)
    app.button(key="clear_profile").click().run()
    app.button(key="load_local").click().run()
    assert app.session_state["ratings"] == {-169: 4}
    app.selectbox(key="algorithm").set_value("Content-based").run()
    app.slider(key="diversity").set_value(.5).run()
    app.selectbox(key="ui_language").set_value("en").run()
    assert not app.exception
    assert app.tabs[0].label == "For you"
    assert app.session_state["ratings"] == {-169: 4}
    assert app.selectbox(key="media_type").value == "Series"
    assert app.selectbox(key="algorithm").value == "Content-based"
    assert app.slider(key="diversity").value == .5
    app.selectbox(key="ui_language").set_value("uk").run()
    app.checkbox(key="localized_only").uncheck().run()
    app.selectbox(key="ui_language").set_value("en").run()
    app.selectbox(key="ui_language").set_value("uk").run()
    assert not app.checkbox(key="localized_only").value
    assert app.session_state["ratings"] == {-169: 4}
