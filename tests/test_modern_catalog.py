"""Synthetic provider contracts, identity boundaries and offline operation."""

import json
import urllib.error
from dataclasses import replace

import numpy as np
import pytest

from app.recommender import Recommender
from src.catalog_view import CatalogView
from src.modern_catalog import CatalogTitle, ModernCatalog, canonical_provider_id, resolve_mapping
from src.providers import (
    CACHE_TTL,
    STALE_LIMIT,
    JsonCache,
    NoRedirect,
    ProviderClient,
    parse_tmdb,
    parse_tvmaze,
    provider_search,
    refresh_catalog,
    title_details,
)


def synthetic_title(**changes):
    values = dict(
        provider="TMDB",
        provider_id=42,
        media_type="Movie",
        original_title="Synthetic arrival",
        title_en="Synthetic arrival",
        title_uk="Синтетичне прибуття",
        release_date="2026-10-01",
        genres=("Sci-Fi",),
        summary_en="A synthetic fixture, not real film data.",
        community_rating=7.5,
        vote_count=100,
    )
    return CatalogTitle(**(values | changes))


def tv_show(**changes):
    return {
        "id": 42,
        "name": "Synthetic series",
        "type": "Scripted",
        "premiered": "2026-09-01",
        "language": "English",
        "genres": ["Science-Fiction"],
        "summary": "<p>Real <b>provider text</b>.</p><script>bad()</script>",
        "rating": {"average": 8},
        "image": {"medium": "https://static.tvmaze.com/uploads/test.jpg"},
        "runtime": 45,
        "externals": {"imdb": "tt1234567"},
    } | changes


def test_namespaces_never_alias_equal_numeric_ids_or_media_types():
    assert canonical_provider_id("TVmaze", 42, "Series") == -42
    assert (
        len(
            {
                canonical_provider_id(p, 42, kind)
                for p, kind in [("TVmaze", "Series"), ("TMDB", "Movie"), ("TMDB", "Series")]
            }
        )
        == 3
    )
    for value in (True, 0, -1, 1_000_000_000, "42"):
        with pytest.raises(ValueError):
            canonical_provider_id("TMDB", value, "Movie")


def test_mapping_requires_unique_imdb_type_and_year(sample):
    movies, _ = sample
    movies["media_type"], movies["source"] = "Movie", "MovieLens"
    movies["imdb_id"] = ""
    movies.loc[0, "imdb_id"] = "tt1234567"
    title = synthetic_title(imdb_id="tt1234567", release_date="1995-01-01")
    assert resolve_mapping(title, movies) == (1, "unique_imdb_type_year")
    for different in (
        replace(title, release_date="2026-01-01"),
        replace(title, media_type="Series"),
    ):
        assert resolve_mapping(different, movies)[1] == "separate_provider_identity"
    movies.loc[1, "imdb_id"] = "tt1234567"
    assert resolve_mapping(title, movies)[1] == "separate_provider_identity"


def test_duplicate_names_keep_distinct_identities_and_atomic_snapshot(tmp_path):
    titles = [
        synthetic_title(),
        synthetic_title(provider_id=43, release_date="1995-01-01"),
        synthetic_title(provider_id=42, media_type="Series"),
    ]
    catalog = ModernCatalog(titles)
    path = tmp_path / "catalog.json"
    catalog.save(path)
    restored = ModernCatalog.load(path)
    assert restored.titles == catalog.titles and len(restored.titles) == 3
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["titles"].append(raw["titles"][0])
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="Duplicate"):
        ModernCatalog.load(path)


@pytest.mark.parametrize(
    "changes",
    [
        {"poster_url": "https://evil.test/poster.jpg"},
        {"poster_url": "javascript:alert(1)"},
        {"community_rating": float("nan")},
        {"community_rating": True},
        {"release_date": "2026-99-99"},
        {"vote_count": -1},
        {"runtime": 2000},
        {"trailer_url": "https://www.youtube.com/watch?v=unsafe<script>"},
        {"imdb_id": "ttOTHER"},
        {"cast": ("a" * 151,)},
    ],
)
def test_untrusted_metadata_rejected(changes):
    with pytest.raises(ValueError):
        synthetic_title(**changes)


def test_provider_text_and_language_fallback_are_real_not_generated():
    title = parse_tvmaze(tv_show())
    assert title.genres == ("Sci-Fi",)
    assert title.summary("uk") == "Real provider text ." and "bad" not in title.summary("en")
    assert title.source_url == "https://www.tvmaze.com/shows/42"
    missing = replace(
        title, poster_url="", community_rating=None, summary_en="", summary_original=""
    )
    assert (
        missing.poster_url == ""
        and missing.community_rating is None
        and missing.summary("uk") == ""
    )
    fixture = {
        "id": 1,
        "title": "English fixture",
        "original_title": "Original fixture",
        "overview": "English synopsis",
        "vote_count": 0,
        "vote_average": 0,
        "release_date": "2026-10-01",
        "videos": {
            "results": [
                {"site": "YouTube", "type": "Trailer", "official": False, "key": "abcdefghijk"},
                {"site": "YouTube", "type": "Trailer", "official": True, "key": "lmnopqrstuv"},
            ]
        },
    }
    parsed = parse_tmdb(fixture, uk={"id": 1, "title": "Українська назва", "overview": ""})
    assert parsed.title("uk") == "Українська назва" and parsed.summary("uk") == "English synopsis"
    assert parsed.community_rating is None and parsed.trailer_url.endswith("lmnopqrstuv")
    assert parse_tmdb(fixture, uk={"id": 2, "title": "Wrong identity"}).title_uk == ""


def test_cache_expiration_offline_failure_and_original_fetch_time(tmp_path):
    now = [100_000.0]
    calls = []

    def transport(url, headers):
        calls.append(url)
        return {"id": 42}

    cache = JsonCache(tmp_path)
    client = ProviderClient(cache, transport=transport, clock=lambda: now[0], sleep=lambda _: None)
    assert client.fetch("TVmaze", "/shows/42").status == "offline" and not calls
    first = client.fetch("TVmaze", "/shows/42", online=True)
    now[0] += 100
    cached = client.fetch("TVmaze", "/shows/42", online=True)
    assert cached.status == "cache" and cached.fetched_at == first.fetched_at and len(calls) == 1
    now[0] += CACHE_TTL
    assert client.fetch("TVmaze", "/shows/42").status == "stale"

    def unavailable(*_):
        raise OSError("SECRET token must not be displayed")

    client.transport = unavailable
    result = client.fetch("TVmaze", "/shows/42", online=True)
    assert result.status == "stale" and "SECRET" not in str(result)
    now[0] += STALE_LIMIT
    assert client.fetch("TVmaze", "/shows/42").payload is None


def test_rate_limit_cooldown_no_credential_leak_or_redirect(tmp_path):
    calls = []

    def limited(url, headers):
        calls.append((url, headers))
        raise urllib.error.HTTPError(url, 429, "limited", {"Retry-After": "60"}, None)

    client = ProviderClient(
        JsonCache(tmp_path),
        token="test-secret",
        transport=limited,
        clock=lambda: 100_000,
        sleep=lambda _: None,
    )
    first = client.fetch("TMDB", "/movie/42", online=True)
    assert (
        first.status == "rate_limited"
        and client.fetch("TMDB", "/movie/43", online=True).status == "rate_limited"
    )
    assert len(calls) == 1 and "test-secret" not in calls[0][0]
    assert not list(tmp_path.glob("*.json")) and "test-secret" not in str(first)
    assert (
        ProviderClient(JsonCache(tmp_path), token="").fetch("TMDB", "/movie/42", online=True).status
        == "missing_credentials"
    )
    assert NoRedirect().redirect_request(None, None, 302, None, None, "https://evil.test") is None
    with pytest.raises(ValueError):
        client.fetch("TVmaze", "https://evil.test")
    with pytest.raises(ValueError):
        client.fetch("TVmaze", "/shows", {"api_key": "private"})


def test_cache_capacity_corruption_and_feed_item_validation(tmp_path):
    cache = JsonCache(tmp_path, max_entries=2)
    for index in range(3):
        cache.write(str(index), {"id": index}, 100_000 + index)
    assert len(list(tmp_path.glob("*.json"))) == 2
    cache.path("corrupt").write_text("{broken")
    assert cache.read("corrupt", 100_004) is None

    def transport(url, headers):
        if "/search/shows" in url:
            return [{"show": tv_show()}, {"show": tv_show(id=True)}, "bad"]
        if "/shows?" in url:
            return [tv_show(), tv_show(id=-1)]
        return []

    client = ProviderClient(cache, token="", transport=transport, sleep=lambda _: None)
    titles, statuses = provider_search(client, "fixture", online=True)
    assert len(titles) == 1 and statuses["TMDB"] == "missing_credentials"
    assert len(refresh_catalog(client, online=True)[0]) == 1


def test_details_must_match_requested_provider_id(tmp_path):
    client = ProviderClient(
        JsonCache(tmp_path),
        token="test-secret",
        transport=lambda *_: {"id": 999, "title": "Other title"},
        sleep=lambda _: None,
    )
    title = synthetic_title()
    assert title_details(client, title, online=True)[0] == title


def test_facade_does_not_refit_or_change_production_models(sample):
    base = Recommender(*sample)
    before = base.score_components({1: 5, 2: 1})
    factors = base.collaborative.item_factors.copy()
    view = CatalogView(base, ModernCatalog([synthetic_title()]))
    for name, values in before.items():
        np.testing.assert_array_equal(base.score_components({1: 5, 2: 1})[name], values)
    np.testing.assert_array_equal(base.collaborative.item_factors, factors)
    assert view.recommend_known({1: 5, synthetic_title().canonical_id: 4}) == base.recommend(
        {1: 5}, "Adaptive"
    )
    results = view.modern_recommend({1: 5})
    assert results and results[0][0] == synthetic_title().canonical_id
    assert view.normalize_id(-1_000_000_000_042) == -1_000_000_000_042


def test_saved_identity_references_restore_without_metadata_or_mutation(sample):
    view = CatalogView(Recommender(*sample), ModernCatalog([synthetic_title()]))
    mid = synthetic_title().canonical_id
    refs = view.export_references({1, mid})
    offline = CatalogView(view.base)
    candidate = offline.with_references(refs)
    assert candidate.normalize_id(mid) == mid and candidate.reference_only == {mid}
    assert mid not in offline.positions and candidate.titles[mid].community_rating is None
    refs[str(mid)]["provider_id"] = 99
    with pytest.raises(ValueError, match="namespace"):
        offline.with_references(refs)
    assert mid not in offline.positions
