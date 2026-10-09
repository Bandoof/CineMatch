"""Read MovieLens 100K and split at shared, global time boundaries."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.catalog import canonical_catalog

ROOT = Path(__file__).resolve().parents[1]
GENRES = [
    "unknown", "Action", "Adventure", "Animation", "Children's", "Comedy", "Crime",
    "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "Musical", "Mystery",
    "Romance", "Sci-Fi", "Thriller", "War", "Western",
]


def load_movielens(directory: Path | str = ROOT / "data" / "ml-100k"):
    directory = Path(directory)
    for filename in ("u.data", "u.item"):
        if not (directory / filename).is_file():
            raise FileNotFoundError(
                "MovieLens is not installed. Run: python -m scripts.download_data"
            )
    ratings = pd.read_csv(
        directory / "u.data", sep="\t", header=None,
        names=["user_id", "movie_id", "rating", "timestamp"],
    )
    movies = pd.read_csv(
        directory / "u.item", sep="|", header=None, encoding="latin-1",
        names=["movie_id", "title", "release_date", "video_release", "imdb_url", *GENRES],
    )
    movies["year"] = pd.to_numeric(
        movies.title.str.extract(r"\((\d{4})\)\s*$", expand=False), errors="coerce"
    ).fillna(0).astype(int)
    movies["genres"] = movies.apply(
        lambda row: tuple(g for g in GENRES if row[g] == 1), axis=1
    )
    movies = movies.sort_values("movie_id").reset_index(drop=True)
    if ratings.empty or ratings.duplicated(["user_id", "movie_id"]).any():
        raise ValueError("Ratings must be nonempty with unique user/movie pairs.")
    if not ratings.rating.between(1, 5).all():
        raise ValueError("MovieLens ratings must be between 1 and 5.")
    if not set(ratings.movie_id).issubset(set(movies.movie_id)):
        raise ValueError("A rating refers to an unknown movie.")
    movies, ratings, _ = canonical_catalog(movies, ratings)
    return movies, ratings


def fingerprint(movies: pd.DataFrame, ratings: pd.DataFrame) -> str:
    """Fingerprint catalog ordering AND training values, not just row count."""
    digest = hashlib.sha256()
    digest.update(pd.util.hash_pandas_object(movies, index=False).values.tobytes())
    digest.update(pd.util.hash_pandas_object(ratings, index=False).values.tobytes())
    return digest.hexdigest()


def temporal_split(ratings: pd.DataFrame):
    """80/10/10 by global time, keeping equal timestamps on the same side."""
    if len(ratings) < 10:
        raise ValueError("At least 10 ratings are needed for a temporal split.")
    ordered = np.sort(ratings.timestamp.to_numpy())
    train_cutoff = int(ordered[int(len(ordered) * 0.8) - 1])
    validation_cutoff = int(ordered[int(len(ordered) * 0.9) - 1])
    train = ratings[ratings.timestamp <= train_cutoff].copy()
    validation = ratings[
        (ratings.timestamp > train_cutoff) & (ratings.timestamp <= validation_cutoff)
    ].copy()
    test = ratings[ratings.timestamp > validation_cutoff].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError("Timestamp ties prevent a nonempty temporal split.")
    return train, validation, test


def load_app_movies(directory=ROOT / "data" / "ml-100k", modern_directory=None):
    from src.movies import extend_movies
    movies, ratings = load_movielens(directory)
    modern_directory = modern_directory or Path(directory).parent / "ml-latest-small"
    return extend_movies(movies, ratings, modern_directory)
