"""New default UI flows; provider fixtures are synthetic, not live API evidence."""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.memory import MemoryStore
from src.modern_catalog import CatalogTitle, ModernCatalog
from src.profiles import parse_profile


@pytest.fixture
def product(dataset_dir, tmp_path, monkeypatch):
    monkeypatch.delenv("CINEMATCH_UI", raising=False)
    paths = {
        "CINEMATCH_DATA_DIR": dataset_dir,
        "CINEMATCH_DISCOVERY_DIR": tmp_path / "discovery",
        "CINEMATCH_ARTIFACT_ROOT": tmp_path,
        "CINEMATCH_SERIES_FILE": tmp_path / "none-series",
        "CINEMATCH_METADATA_FILE": tmp_path / "none-metadata",
        "CINEMATCH_CONTENT_FILE": tmp_path / "none-content",
        "CINEMATCH_PROFILE_DB": tmp_path / "profiles.sqlite3",
    }
    for key, value in paths.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("CINEMATCH_DEFAULT_LANGUAGE", "en")
    monkeypatch.setenv("CINEMATCH_LOCAL_PROFILES", "1")
    monkeypatch.setenv("CINEMATCH_AUTOSAVE", "1")
    ModernCatalog(
        [
            CatalogTitle(
                "TVmaze",
                101,
                "Series",
                "Synthetic Northern Light",
                title_uk="Синтетичне сяйво",
                genres=("Drama",),
                release_date=date.today().isoformat(),
                summary_en="A synthetic test synopsis.",
                community_rating=8.5,
                runtime=45,
            )
        ]
    ).save(paths["CINEMATCH_DISCOVERY_DIR"] / "catalog.json")
    return AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"), default_timeout=30
    ), paths


def healthy(app):
    assert not app.exception
    assert not any("Temporarily unavailable" in heading.value for heading in app.subheader)


def test_first_launch_and_all_pages_render_only_active_controls(product):
    app, _ = product
    app.run()
    healthy(app)
    assert any("Stories that stay" in title.value for title in app.title)
    assert not any(w.key == "query_search" for w in app.text_input)
    for page in ("for_you", "movies", "series", "search", "library", "research", "discover"):
        app.radio(key="navigation").set_value(page).run()
        healthy(app)
    app.button(key="hero_search").click().run()
    assert app.radio(key="navigation").value == "search"
    healthy(app)


def test_search_details_watchlist_rating_undo_and_fresh_restore(product):
    app, paths = product
    app.run().radio(key="navigation").set_value("search").run()
    app.text_input(key="query_search").set_value("Синтетичне сяйво").run()
    healthy(app)
    app.button(key="details_search_-101").click().run()
    assert app.session_state["watched"] == set()  # A click is not a viewing event.
    app.button(key="detail_watchlist").click().run()
    assert app.session_state["watchlist"] == {-101}
    app.button(key="library_undo_button").click().run()
    assert app.session_state["watchlist"] == set()
    app.button(key="detail_watchlist").click().run()
    app.select_slider(key="stars_-101").set_value(4.5).run()
    next(w for w in app.button if w.label == "Save rating").click().run()
    healthy(app)
    assert app.session_state["ratings"] == {-101: 4.5}
    assert app.session_state["watched"] == {-101}
    assert not app.session_state["watchlist"]
    # Persisted identity survives loss of provider metadata, without fabricated fields.
    (paths["CINEMATCH_DISCOVERY_DIR"] / "catalog.json").unlink()
    restored = AppTest.from_file(app._script_path, default_timeout=30).run()
    healthy(restored)
    assert restored.session_state["ratings"] == {-101: 4.5}
    view = restored.session_state["_catalog_view"]
    assert view.reference_only == {-101} and not view.titles[-101].poster_url
    assert view.titles[-101].community_rating is None
    revision, doc = MemoryStore(paths["CINEMATCH_PROFILE_DB"]).read()
    assert revision > 0 and parse_profile(doc["profile"])["schema_version"] == 6


def test_ukrainian_ui_library_filters_named_profiles_and_navigation(product):
    app, _ = product
    app.run().selectbox(key="ui_language").set_value("uk").run()
    healthy(app)
    app.button(key="details_discover_-101").click().run()
    app.button(key="detail_watchlist").click().run()
    app.radio(key="navigation").set_value("library").run()
    healthy(app)
    assert not any(w.key == "detail_watchlist" for w in app.button)
    app.text_input(key="profile_name").set_value("Моя копія").run()
    app.button(key="profile_save").click().run()
    healthy(app)
    app.run()  # Saved names appear on the next rerun.
    app.button(key="profile_load").click().run()
    assert app.session_state["watchlist"] == {-101}
    app.text_input(key="library_query").set_value("no-match-example").run()
    assert not any(str(w.key).startswith("details_library") for w in app.button)
    app.text_input(key="library_query").set_value("syntetychne siaivo").run()
    assert app.button(key="details_library_-101")
    healthy(app)


def test_modern_only_offline_first_launch_without_training_data(product, monkeypatch):
    app, paths = product
    monkeypatch.setenv("CINEMATCH_DATA_DIR", str(paths["CINEMATCH_ARTIFACT_ROOT"] / "absent-data"))
    app.run()
    healthy(app)
    assert app.session_state["_catalog_view"].base is None
    app.radio(key="navigation").set_value("for_you").run()
    healthy(app)
    next(w for w in app.button if w.label == "Rate").click().run()
    assert app.session_state["ratings"] == {-101: 4.0}
    healthy(app)


def test_corrupt_snapshot_preserved_and_empty_states_render(product):
    app, paths = product
    target = paths["CINEMATCH_DISCOVERY_DIR"] / "catalog.json"
    target.write_text("broken snapshot", encoding="utf-8")
    app.run()
    healthy(app)
    assert target.read_text(encoding="utf-8") == "broken snapshot"
    assert any("preserved" in message.value for message in app.warning)


def test_search_index_cache_and_metadata_invalidation(product):
    app, paths = product
    app.run().radio(key="navigation").set_value("search").run()
    first = app.session_state["_search_index"]
    app.text_input(key="query_search").set_value("Test film").run()
    assert app.session_state["_search_index"] is first
    ModernCatalog([CatalogTitle("TVmaze", 102, "Series", "Synthetic Replacement")]).save(
        paths["CINEMATCH_DISCOVERY_DIR"] / "catalog.json"
    )
    app.text_input(key="query_search").set_value("Replacement").run()
    healthy(app)
    assert app.session_state["_search_index"] is not first
    assert app.button(key="details_search_-102")


def test_provider_failure_keeps_cached_titles_and_private_ratings(product, monkeypatch):
    import urllib.error

    import app.product_ui as ui
    from src.providers import JsonCache, ProviderClient

    app, paths = product

    def unavailable(url, headers):
        raise urllib.error.URLError("synthetic outage with a secret that must not render")

    client = ProviderClient(
        JsonCache(paths["CINEMATCH_DISCOVERY_DIR"] / "responses"),
        transport=unavailable,
        token="",
        sleep=lambda _: None,
    )
    monkeypatch.setattr(ui, "provider_client", lambda *args: client)
    app.run()
    original = (paths["CINEMATCH_DISCOVERY_DIR"] / "catalog.json").read_bytes()
    app.button(key="refresh_catalog").click().run()
    healthy(app)
    assert -101 in app.session_state["_catalog_view"].rows
    assert (paths["CINEMATCH_DISCOVERY_DIR"] / "catalog.json").read_bytes() == original
    assert client.requests == 1  # Failure cooldown prevents a second TVmaze call.
    assert app.session_state["ratings"] == {}
    assert not any("secret" in w.value for w in app.caption)


def test_unwritable_profile_store_preserves_session_actions_and_neutral_error(product, monkeypatch):
    app, paths = product
    monkeypatch.setenv(
        "CINEMATCH_PROFILE_DB", str(paths["CINEMATCH_ARTIFACT_ROOT"])
    )  # A directory cannot be SQLite.
    app.run()
    healthy(app)
    app.button(key="watch_discover_-101").click().run()
    healthy(app)
    assert app.session_state["watchlist"] == {-101}
    assert app.warning and app.session_state["_memory_error"] == "memory_failed"


def test_historical_only_discovery_has_useful_default(product):
    app, paths = product
    (paths["CINEMATCH_DISCOVERY_DIR"] / "catalog.json").unlink()
    app.run()
    healthy(app)
    assert app.selectbox(key="discovery_shelf").value == "popular"
    assert any(str(button.key).startswith("details_discover_") for button in app.button)
