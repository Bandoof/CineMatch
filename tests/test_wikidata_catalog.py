"""Synthetic response contracts and integrity of the separately labeled real sample."""

import hashlib
import json
from pathlib import Path

import pytest

from src.catalog_view import CatalogView
from src.discovery_search import SearchIndex, catalog_records
from src.modern_catalog import CatalogTitle, ModernCatalog, canonical_provider_id
from src.profiles import export_profile, import_library_profile
from src.providers import JsonCache, ProviderClient
from src.wikidata_catalog import localize_series, parse_entity, read_entities


def claim(value):
    return {"mainsnak": {"datavalue": {"value": value}}, "rank": "normal"}


def entity():
    return {
        "id": "Q42",
        "labels": {"en": {"value": "Synthetic title"}, "uk": {"value": "Синтетична назва"}},
        "descriptions": {"uk": {"value": "Синтетичний короткий опис"}},
        "claims": {
            "P345": [claim("tt1234567")],
            "P577": [claim({"time": "+2025-04-16T00:00:00Z", "precision": 11})],
            "P136": [claim({"id": "Q1"})],
            "P57": [claim({"id": "Q2"})],
            "P2047": [claim({"amount": "+100", "unit": "http://www.wikidata.org/entity/Q7727"})],
        },
    }


def test_real_fields_missing_data_and_separate_namespaces():
    title = parse_entity(
        entity(),
        "Movie",
        {
            "Q1": {"labels": {"en": {"value": "drama film"}}},
            "Q2": {"labels": {"en": {"value": "Synthetic Director"}}},
        },
        1_700_000_000,
    )
    assert title.title_uk == "Синтетична назва" and title.genres == ("Drama",)
    assert title.runtime == 100 and title.creators == ("Synthetic Director",)
    assert title.community_rating is None and not title.poster_url and not title.summary_uk
    assert title.short_description_uk and title.localization_source.endswith("Q42")
    assert (
        len(
            {
                canonical_provider_id(p, 42, k)
                for p, k in [
                    ("TVmaze", "Series"),
                    ("TMDB", "Movie"),
                    ("TMDB", "Series"),
                    ("Wikidata", "Movie"),
                    ("Wikidata", "Series"),
                ]
            }
        )
        == 5
    )


def test_ambiguous_identity_and_date_statements_are_not_invented():
    data = entity()
    data["claims"]["P345"].append(claim("tt2345678"))
    data["claims"]["P577"].append(claim({"time": "+2025-12-31T00:00:00Z", "precision": 11}))
    title = parse_entity(data, "Movie", {})
    assert not title.imdb_id and not title.release_date
    assert title.year == 2025
    data["claims"]["P577"] = [claim({"time": "+2025-01-01T00:00:00Z", "precision": 9})]
    assert not parse_entity(data, "Movie", {}).release_date


def test_only_bounded_read_api_and_offline_cache_no_credentials(tmp_path):
    calls = []

    def transport(url, headers):
        calls.append((url, headers))
        return {"entities": {"Q42": entity()}}

    client = ProviderClient(
        JsonCache(tmp_path), token="must-not-forward", transport=transport, sleep=lambda _: None
    )
    records, stamps, status = read_entities(client, ["Q42"], online=True)
    assert status == "fetched" and records["Q42"]["id"] == "Q42" and stamps["Q42"]
    assert "Authorization" not in calls[0][1] and "www.wikidata.org/w/api.php" in calls[0][0]
    assert read_entities(client, ["Q42"], online=False)[2] == "cache" and len(calls) == 1
    with pytest.raises(ValueError):
        client.fetch("Wikidata", "/w/api.php", {"action": "edit", "format": "json"}, online=True)
    with pytest.raises(ValueError):
        read_entities(client, ["Q42"] * 81 + ["malicious"])


def test_cross_provider_identity_dedup_preserves_remakes_and_profile_roundtrip():
    wiki = parse_entity(entity(), "Movie", {})
    tmdb = CatalogTitle(
        "TMDB", 42, "Movie", "Synthetic title", imdb_id=wiki.imdb_id, release_date=wiki.release_date
    )
    remake = CatalogTitle(
        "TMDB", 43, "Movie", "Synthetic title", imdb_id=wiki.imdb_id, release_date="1990-01-01"
    )
    view = CatalogView(None, ModernCatalog([wiki, tmdb, remake]))
    assert len(view.rows) == 2 and view.normalize_id(wiki.canonical_id) == tmdb.canonical_id
    assert view.display_title(tmdb.canonical_id, "uk").startswith(wiki.title_uk)
    payload = export_profile(view, {wiki.canonical_id: 5}, set())
    fresh = CatalogView(None)
    assert import_library_profile(fresh, payload)[0] == {tmdb.canonical_id: 5}
    duplicate = CatalogTitle(
        "Wikidata",
        43,
        "Movie",
        "Synthetic duplicate",
        imdb_id=wiki.imdb_id,
        release_date=wiki.release_date,
    )
    ambiguous = CatalogView(None, ModernCatalog([wiki, tmdb, duplicate]))
    assert len(ambiguous.rows) == 3


def test_series_localization_requires_verified_identity_year_and_source():
    wiki = parse_entity(entity(), "Series", {})
    series = CatalogTitle(
        "TVmaze",
        42,
        "Series",
        "Synthetic title",
        imdb_id=wiki.imdb_id,
        release_date=wiki.release_date,
    )
    localized = localize_series(series, [wiki])
    assert localized.provider == "TVmaze" and localized.title_uk == wiki.title_uk
    assert localized.localization_source == wiki.source_url and localized.summary_uk == ""
    assert localize_series(series, [wiki, wiki]) == series


def test_frozen_real_sample_integrity_coverage_and_uk_search():
    root = Path(__file__).resolve().parents[1] / "assets/demo"
    coverage = json.loads((root / "coverage.json").read_text(encoding="utf-8"))
    assert (
        hashlib.sha256((root / "catalog.json").read_bytes()).hexdigest()
        == coverage["snapshot_sha256"]
    )
    catalog = ModernCatalog.load(root / "catalog.json")
    assert len(catalog.titles) == coverage["total"] == 30
    assert sum(t.media_type == "Movie" for t in catalog.titles.values()) == 22
    assert sum(bool(t.title_uk) for t in catalog.titles.values()) == 30
    view = CatalogView(None, catalog)
    index = SearchIndex(catalog_records(view))
    for query in ("Інтерстеллар", "interstellar", "Матриця", "Пуститися берега", "Останні з нас"):
        assert index.search(query)
    assert all(
        t.community_rating is None and not t.poster_url
        for t in catalog.titles.values()
        if t.provider == "Wikidata"
    )
