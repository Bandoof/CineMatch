"""TMDB is disabled; old local profiles keep working and their original is kept once."""

import json

from src.catalog_view import CatalogView
from src.memory import MemoryStore
from src.modern_catalog import ModernCatalog
from src.profiles import export_profile, import_library_profile, strip_legacy_tmdb
from tests.test_catalog_explorer import explorer
from tests.test_library import make_app
from tests.test_memory import fresh_app
from tests.test_modern_catalog import synthetic_title

LEGACY_MOVIE = -1_000_000_000_042  # Former TMDB movie namespace.
LEGACY_REF = {
    "provider": "TMDB",
    "provider_id": 42,
    "media_type": "Movie",
    "original_title": "Old provider title",
}


def test_strip_removes_only_legacy_identities_in_every_profile_format():
    title = synthetic_title()
    view = CatalogView(None, ModernCatalog([title]))
    document = json.loads(export_profile(view, {title.canonical_id: 4}, set()))
    document["ratings"].append({"item_id": LEGACY_MOVIE, "rating": 5})
    for name in ("watched", "blocked", "topic_blocked"):
        document[name].append(LEGACY_MOVIE)
    document["catalog_refs"][str(LEGACY_MOVIE)] = LEGACY_REF
    payload = json.dumps(document)
    cleaned, removed = strip_legacy_tmdb(payload)
    assert removed == 1 and str(LEGACY_MOVIE) not in cleaned
    assert import_library_profile(CatalogView(None), payload)[0] == {title.canonical_id: 4}
    # Unchanged payloads are returned as-is, including the original {id: rating} export.
    untouched = export_profile(view, {title.canonical_id: 4}, set())
    assert strip_legacy_tmdb(untouched) == (untouched, 0)
    assert strip_legacy_tmdb(json.dumps({"1": 4, str(LEGACY_MOVIE): 5}))[1] == 1


def test_old_catalog_snapshot_hides_tmdb_records_with_a_short_notice(tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    ModernCatalog([synthetic_title()]).save(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["titles"].append(dict(raw["titles"][0], provider="TMDB", provider_id=7))
    path.write_text(json.dumps(raw), encoding="utf-8")
    before = path.read_bytes()
    app = explorer(tmp_path, monkeypatch)
    assert not app.exception and path.read_bytes() == before
    assert any("Hidden 1 old TMDB" in caption.value for caption in app.caption)
    assert [x.value for x in app.subheader] == ["Синтетичне прибуття"]


def test_autosaved_profile_with_tmdb_entries_is_backed_up_once_then_restored(
    dataset_dir, monkeypatch
):
    app = make_app(dataset_dir, monkeypatch)
    app.button(key="guide_rate_4").click().run()
    personal = dict(app.session_state["ratings"])
    store = MemoryStore(dataset_dir / "profiles.sqlite3")
    revision, document = store.read()
    profile = json.loads(document["profile"])
    profile["ratings"].append({"item_id": LEGACY_MOVIE, "rating": 5})
    profile["watched"].append(LEGACY_MOVIE)
    profile.update(schema_version=6, catalog_refs={str(LEGACY_MOVIE): LEGACY_REF})
    document["profile"] = json.dumps(profile)
    store.write(document, revision)
    original = store.read()[1]

    restored = fresh_app()
    assert not restored.exception and "_memory_error" not in restored.session_state
    assert restored.session_state["ratings"] == personal
    backup = dataset_dir / "profiles.sqlite3.pre-tmdb-removal.json"
    assert json.loads(backup.read_text(encoding="utf-8")) == original
    assert any("TMDB" in caption.value for caption in restored.caption)
    # Autosave now stores the profile without TMDB entries; the first copy is never replaced.
    assert str(LEGACY_MOVIE) not in store.read()[1]["profile"]
    kept = backup.read_bytes()
    fresh_app()
    assert backup.read_bytes() == kept
