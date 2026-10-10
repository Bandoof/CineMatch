"""Search quality cases retain remakes/media identities and run entirely offline."""

from datetime import date

import pytest

from app.recommender import Recommender
from src.catalog_view import CatalogView
from src.discovery_collections import collections
from src.discovery_search import SearchIndex, SearchRecord, catalog_records, transliterate
from src.modern_catalog import ModernCatalog
from tests.test_modern_catalog import synthetic_title


@pytest.fixture
def index():
    entries = [
        (1, ("Interstellar (2014)", "Інтерстеллар"), "Movie", 2014, ("Sci-Fi",), 8.5),
        (2, ("Léon (1994)", "Professional, The (1994)", "Леон"), "Movie", 1994, ("Crime",), 8),
        (3, ("Breaking Bad (2008)", "Пуститися берега"), "Series", 2008, ("Crime",), 9),
        (4, ("It (2017)", "Воно"), "Movie", 2017, ("Horror",), 7),
        (5, ("It (1990)",), "Series", 1990, ("Horror",), 6),
        (6, ("Intouchables (2011)", "1+1"), "Movie", 2011, ("Comedy",), 8),
        (7, ("The Thing (2011)", "Дещо"), "Movie", 2011, ("Horror",), 6),
        (8, ("The Thing (1982)", "Дещо"), "Movie", 1982, ("Horror",), 8),
        (9, ("1917 (2019)",), "Movie", 2019, ("War",), None),
        (10, ("C++",), "Movie", 2026, ("Comedy",), None),
    ]
    return SearchIndex(
        SearchRecord(mid, titles, kind, year, genres, rating)
        for mid, titles, kind, year, genres, rating in entries
    )


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Interstellar", 1),
        ("Інтерстеллар", 1),
        ("interstelar", 1),
        ("Інтрстеллар", 1),
        ("Leon", 2),
        ("The Professional", 2),
        ("Пуститися bad", 3),
        ("pustytysia bereha", 3),
        ("breking bad", 3),
        ("1 + 1", 6),
        ("The Thing (1982)", 8),
        ("1917", 9),
        ("C++", 10),
    ],
)
def test_realistic_title_cases_rank_correct_identity_first(index, query, expected):
    assert index.search(query)[0].item_id == expected


def test_identical_names_short_queries_filters_and_unknown_ratings(index):
    assert {h.item_id for h in index.search("It")} >= {4, 5}
    assert [h.item_id for h in index.search("It", media_type="Series")] == [5]
    assert {h.item_id for h in index.search("Дещо")} == {7, 8}
    assert [h.item_id for h in index.search("Дещо", year_range=(2010, 2020))] == [7]
    assert [h.item_id for h in index.search("", genres=("War",), min_rating=1)] == []
    assert [h.item_id for h in index.search("", genres=("War",))] == [9]
    assert index.search("", limit=2) == index.search("", limit=None)[:2]
    assert index.search("ZZZZ entirely unmatched") == []
    with pytest.raises(ValueError):
        index.search("query", sort="trending")


def test_transliteration_word_initials_and_originals_retained():
    assert transliterate("Київ Юлія Єва") == "kyiv yuliia yeva"
    assert transliterate("Інтерстеллар") == "interstellar"


def test_catalog_records_preserve_localized_aliases_and_provider_sources(sample):
    base = Recommender(*sample)
    base.metadata.items[1] = {"title_uk": "Перший фільм", "search_aliases": ["First movie"]}
    title = synthetic_title()
    view = CatalogView(base, ModernCatalog([title]))
    index = SearchIndex(catalog_records(view))
    assert index.search("Перший фільм")[0].item_id == 1
    assert index.search("First movie")[0].item_id == 1
    assert index.search("Синтетичне прибуття")[0].item_id == title.canonical_id
    assert index.records[title.canonical_id].rating_10 == 7.5


def test_collections_use_actual_dates_votes_and_saved_preferences(sample):
    base = Recommender(*sample)
    recent = synthetic_title()
    upcoming = synthetic_title(provider_id=43, release_date="2026-12-01", runtime=90)
    old = synthetic_title(provider_id=44, release_date="2010-01-01", runtime=110)
    view = CatalogView(base, ModernCatalog([recent, upcoming, old]))
    shelves = collections(view, {1: 5}, today=date(2026, 10, 10))
    assert shelves["recent"] == [recent.canonical_id]
    assert shelves["upcoming"] == [upcoming.canonical_id]
    assert (
        upcoming.canonical_id not in shelves["tonight"] and old.canonical_id in shelves["tonight"]
    )
    assert shelves["seed"] == 1 and shelves["because_liked"]
    expected = sorted(
        (int(mid) for mid in base.movie_ids if mid != 1),
        key=lambda mid: (-base.popularity.counts[base.positions[mid]], mid),
    )
    assert shelves["popular"] == expected
    hidden = collections(view, {1: 5}, excluded={recent.canonical_id}, today=date(2026, 10, 10))
    assert not hidden["recent"]
    assert collections(view, today=date(2026, 10, 10))["because_liked"] == []
