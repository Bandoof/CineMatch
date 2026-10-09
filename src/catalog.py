"""Canonical identity without dropping historical rating events across time boundaries."""

import re

import pandas as pd


def integer_id(value):
    if isinstance(value, bool) or not re.fullmatch(r"-?[0-9]+", str(value)):
        raise ValueError("Item IDs must be integers.")
    return int(value)


def canonical_catalog(movies, ratings):
    movies = movies.copy()
    if movies.movie_id.duplicated().any():
        raise ValueError("Catalog IDs must be unique.")
    if "media_type" not in movies:
        movies["media_type"] = "Movie"
    if "source" not in movies:
        movies["source"] = "MovieLens"
    movies["media_type"] = movies["media_type"].fillna("Movie")
    movies["source"] = movies["source"].fillna("MovieLens")
    keys = []
    for row in movies.to_dict("records"):
        url = row.get("imdb_url")
        # Same lookup URL AND title/year; do not merge unrelated namesakes.
        key = ((row["source"], str(url).strip(), str(row["title"]), int(row["year"]))
               if isinstance(url, str) and url.strip() else (row["source"], int(row["movie_id"])))
        keys.append(key)
    groups = {}
    for row, key in zip(movies.to_dict("records"), keys):
        groups.setdefault(key, []).append(row)
    records, aliases = [], {}
    for group in groups.values():
        representative = min(group, key=lambda r: int(r["movie_id"]))
        record = representative.copy()
        ids = sorted({int(mid) for row in group
                      for mid in row.get("aliases", (row["movie_id"],))})
        canonical_id = int(representative["movie_id"])
        record["aliases"] = tuple(ids)
        record["genres"] = tuple(sorted({g for row in group for g in row["genres"]}))
        for genre in {g for row in group for g in row["genres"]}:
            if genre in record:
                record[genre] = 1
        records.append(record)
        aliases.update({mid: canonical_id for mid in ids})
    result = pd.DataFrame(records).sort_values("movie_id").reset_index(drop=True)
    observations = ratings.copy()
    if not set(observations.movie_id).issubset(aliases):
        raise ValueError("A rating refers to an unknown movie.")
    observations["movie_id"] = observations.movie_id.map(aliases).astype(int)
    # Keep all event timestamps. Collapsing to the global latest event here would
    # let future alias ratings remove observations from an earlier training split.
    return result, observations, aliases


def latest_ratings(ratings):
    """Apply only AFTER choosing the observations available at a time boundary."""
    return (ratings.sort_values("timestamp", kind="stable")
            .drop_duplicates(["user_id", "movie_id"], keep="last").reset_index(drop=True))
