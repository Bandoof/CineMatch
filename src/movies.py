"""Extend MovieLens 100K while preserving every original profile identity."""

from pathlib import Path

import pandas as pd

from src.data import GENRES
from src.search import identity_keys

MOVIE_NAMESPACE = 1_000_000
USER_NAMESPACE = 1_000_000

# Exact, year-specific renamed releases, not fuzzy joins across datasets.
RENAMED = {"Star Wars (1977)": 260, "Empire Strikes Back, The (1980)": 1196,
           "Return of the Jedi (1983)": 1210}


def extend_movies(movies, ratings, directory):
    directory = Path(directory)
    if not (directory / "movies.csv").is_file():
        return movies, ratings
    latest = pd.read_csv(directory / "movies.csv")
    links = pd.read_csv(directory / "links.csv")
    observations = pd.read_csv(directory / "ratings.csv")
    if latest.movieId.duplicated().any() or links.movieId.duplicated().any():
        raise ValueError("Extended film IDs must be unique.")
    if not observations.rating.between(.5, 5).all():
        raise ValueError("Extended ratings must be on MovieLens's real 0.5–5 scale.")
    if not set(observations.movieId) <= set(latest.movieId):
        raise ValueError("Extended rating references an unknown title.")
    keyed = {}
    for row in movies.itertuples():
        for key in identity_keys(row.title):
            keyed.setdefault(key, set()).add(int(row.movie_id))
    records = movies.to_dict("records")
    by_id = {int(row["movie_id"]): row for row in records}
    imdb_ids = links.set_index("movieId").imdbId.to_dict()
    renamed = {mid: title for title, mid in RENAMED.items()}
    mapping = {}
    for row in latest.sort_values("movieId").itertuples():
        matches = set().union(*(keyed.get(key, set()) for key in identity_keys(row.title)))
        if int(row.movieId) in renamed:
            matches |= set(movies.loc[movies.title.eq(renamed[int(row.movieId)]), "movie_id"])
        mid = int(next(iter(matches))) if len(matches) == 1 else MOVIE_NAMESPACE + int(row.movieId)
        mapping[int(row.movieId)] = mid
        imdb = imdb_ids.get(row.movieId)
        imdb = "" if pd.isna(imdb) else f"tt{int(imdb):07}"
        if mid in by_id:
            record = by_id[mid]
            record["aliases"] = tuple(sorted(set(record["aliases"]) | {MOVIE_NAMESPACE + int(row.movieId)}))
            # Alternative release names are presentation/search data, not features.
            record["alternate_title"] = row.title
            record["imdb_id"] = imdb
            continue
        genres = tuple(sorted(g for g in row.genres.split("|") if g in GENRES)) or ("unknown",)
        year = pd.to_numeric(pd.Series([row.title]).str.extract(r"\((\d{4})\)\s*$", expand=False),
                             errors="coerce").fillna(0).iloc[0]
        record = {"movie_id": mid, "title": row.title, "year": int(year), "genres": genres,
                  "media_type": "Movie", "source": "MovieLens", "imdb_id": imdb,
                  "source_url": f"https://movielens.org/movies/{row.movieId}",
                  "imdb_url": f"https://www.imdb.com/title/{imdb}/" if imdb else "",
                  "aliases": (mid,), "alternate_title": row.title}
        record.update({genre: int(genre in genres) for genre in GENRES})
        records.append(record)
        by_id[mid] = record
    observations = observations.rename(columns={"userId": "user_id", "movieId": "movie_id"})
    observations["movie_id"] = observations.movie_id.map(mapping).astype(int)
    observations["user_id"] += USER_NAMESPACE
    combined = pd.DataFrame(records).sort_values("movie_id").reset_index(drop=True)
    combined["imdb_id"] = combined.get("imdb_id", "").fillna("")
    combined["alternate_title"] = combined.alternate_title.fillna(combined.title)
    return combined, pd.concat([ratings, observations], ignore_index=True)
