import json

from tests.test_library import make_app


def test_literal_search_preserves_both_languages_and_watched_titles(dataset_dir, monkeypatch):
    metadata = dataset_dir / "localized.json"
    metadata.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "items": {
                    "1": {"original_title": "Test film 1 (1995)", "title_uk": "Перший фільм"}
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    app = make_app(dataset_dir, monkeypatch)
    monkeypatch.setenv("CINEMATCH_METADATA_FILE", str(metadata))
    app.session_state["watched"] = {1}
    app.run()
    app.text_input(key="query").set_value("Перший фільм").run()
    assert not app.exception
    assert app.selectbox(key="rate_id").value == 1
    app.selectbox(key="ui_language").set_value("uk").run()
    assert app.selectbox(key="rate_id").value == 1
    assert "Перший фільм" in app.selectbox(key="rate_id").options[0]
    app.text_input(key="query").set_value("Test film 1 (1995)").run()
    assert app.selectbox(key="rate_id").value == 1
    app.text_input(key="query").set_value("").run()
    # Ukrainian-only catalog contains one translated title, already watched.
    assert all(widget.key != "rate_id" for widget in app.selectbox)
    assert not app.exception
