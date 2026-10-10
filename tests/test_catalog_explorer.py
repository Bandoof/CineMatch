"""Runnable metadata slice, with real UI and explicitly synthetic provider fixtures."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.modern_catalog import ModernCatalog
from src.providers import FetchResult, ProviderClient
from tests.test_modern_catalog import synthetic_title, tv_show


def explorer(directory, monkeypatch):
    monkeypatch.setenv("CINEMATCH_DISCOVERY_DIR", str(directory))
    monkeypatch.delenv("TMDB_READ_ACCESS_TOKEN", raising=False)
    return AppTest.from_file(
        str(Path(__file__).parents[1] / "app/catalog_explorer.py"), default_timeout=30
    ).run()


def test_offline_first_launch_and_saved_attributed_metadata(tmp_path, monkeypatch):
    app = explorer(tmp_path, monkeypatch)
    assert not app.exception and any("No titles are invented" in x.value for x in app.info)
    ModernCatalog([synthetic_title()]).save(tmp_path / "catalog.json")
    app.run()
    assert not app.exception and any(x.value == "Синтетичне прибуття" for x in app.subheader)
    assert any("not endorsed or certified" in x.value for x in app.caption)


def test_explicit_provider_search_works_without_movie_credentials(tmp_path, monkeypatch):
    def fetch(self, provider, endpoint, params=None, online=False):
        return (
            FetchResult([{"show": tv_show()}], "fetched", 1_000_000)
            if provider == "TVmaze"
            else FetchResult(None, "missing_credentials")
        )

    monkeypatch.setattr(ProviderClient, "fetch", fetch)
    app = explorer(tmp_path, monkeypatch)
    app.text_input[0].set_value("Synthetic series")
    app.button[0].click().run()
    assert not app.exception
    assert len(ModernCatalog.load(tmp_path / "catalog.json").titles) == 1
    assert any("missing_credentials" in x.value for x in app.caption)


def test_corrupt_snapshot_and_api_failure_remain_usable(tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    path.write_text("{corrupt")
    monkeypatch.setattr(
        ProviderClient, "fetch", lambda *args, **kwargs: FetchResult(None, "unavailable")
    )
    app = explorer(tmp_path, monkeypatch)
    assert not app.exception and app.warning and path.read_text() == "{corrupt"
    app.button[1].click().run()
    assert not app.exception and path.read_text() == "{corrupt"
