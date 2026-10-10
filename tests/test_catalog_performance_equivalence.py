"""Indexing changes identity lookup cost, never its ambiguity semantics."""

import pandas as pd
import pytest

from src.modern_catalog import CatalogTitle, identity_index, resolve_mapping


@pytest.mark.parametrize("duplicate", [False, True])
def test_indexed_mapping_exactly_matches_original_evidence_rules(duplicate):
    rows = [
        {
            "movie_id": 1,
            "source": "MovieLens",
            "media_type": "Movie",
            "year": 2024,
            "imdb_id": "tt1234567",
        },
        {
            "movie_id": -2,
            "source": "TVmaze",
            "media_type": "Series",
            "year": 2023,
            "imdb_id": "tt2345678",
        },
        {
            "movie_id": 3,
            "source": "MovieLens",
            "media_type": "Movie",
            "year": 1990,
            "imdb_id": "tt1234567",
        },
    ]
    if duplicate:
        rows.extend([{**rows[0], "movie_id": 4}, dict(rows[1])])
    movies = pd.DataFrame(rows)
    indexed = identity_index(movies)
    for title in (
        CatalogTitle(
            "TMDB", 1, "Movie", "Synthetic Current", release_date="2024-01-01", imdb_id="tt1234567"
        ),
        CatalogTitle(
            "TMDB", 2, "Movie", "Synthetic Remake", release_date="1990-01-01", imdb_id="tt1234567"
        ),
        CatalogTitle(
            "TMDB",
            3,
            "Series",
            "Synthetic Type Mismatch",
            release_date="2024-01-01",
            imdb_id="tt1234567",
        ),
        CatalogTitle("TVmaze", 2, "Series", "Synthetic Provider"),
        CatalogTitle("TVmaze", 9, "Series", "Synthetic Unknown"),
    ):
        assert resolve_mapping(title, movies, indexed) == resolve_mapping(title, movies)
