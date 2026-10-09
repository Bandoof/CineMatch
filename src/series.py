"""Load a credited TVmaze metadata snapshot, without fabricating viewing interactions."""

import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

SERIES_COLUMNS = ["movie_id", "title", "year", "genres", "media_type", "source",
                  "source_url", "poster_url", "provider_rating", "status", "aliases"]


def parse_show(show):
    if not isinstance(show, dict):
        raise ValueError("A show must be a metadata object.")
    if show.get("type") not in ("Scripted", "Animation"):
        return None
    sid = show.get("id")
    if isinstance(sid, bool) or not isinstance(sid, int) or sid <= 0:
        raise ValueError("Invalid TVmaze show ID.")
    name = show.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("TVmaze show name is missing.")
    premiere = show.get("premiered") or ""
    if not isinstance(premiere, str):
        raise ValueError("Invalid premiere date.")
    raw_genres = show.get("genres", [])
    if not isinstance(raw_genres, list) or any(not isinstance(g, str) for g in raw_genres):
        raise ValueError("Invalid genre list.")
    year = int(premiere[:4]) if len(premiere) >= 4 and premiere[:4].isdigit() else 0
    genres = tuple(sorted({"Sci-Fi" if g == "Science-Fiction" else g
                           for g in raw_genres})) or ("unknown",)
    if not isinstance(show.get("rating") or {}, dict) or not isinstance(show.get("image") or {}, dict):
        raise ValueError("Invalid rating or image metadata.")
    average = (show.get("rating") or {}).get("average")
    if average is not None and (isinstance(average, bool) or not 0 <= float(average) <= 10):
        raise ValueError("Invalid TVmaze community rating.")
    source_url = show.get("url", "")
    if urlparse(source_url).hostname != "www.tvmaze.com" or not source_url.startswith("https://"):
        raise ValueError("Unexpected TVmaze attribution URL.")
    poster = (show.get("image") or {}).get("medium") or ""
    if poster and (not poster.startswith("https://") or
                   urlparse(poster).hostname != "static.tvmaze.com"):
        poster = ""
    return {"movie_id": -sid, "title": f"{name} ({year})" if year else name,
            "year": year, "genres": genres, "media_type": "Series", "source": "TVmaze",
            "source_url": source_url, "poster_url": poster,
            "provider_rating": None if average is None else float(average),
            "status": str(show.get("status") or "Unknown"), "aliases": (-sid,)}


def load_series(path: Path | str):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=SERIES_COLUMNS), None
    document = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(document, dict) or document.get("schema_version") != 1
            or document.get("source") != "TVmaze" or not isinstance(document.get("shows"), list)):
        raise ValueError("Unsupported series metadata snapshot.")
    records = [parse_show(show) for show in document["shows"]]
    records = [record for record in records if record is not None]
    frame = pd.DataFrame(records, columns=SERIES_COLUMNS)
    if frame.movie_id.duplicated().any():
        raise ValueError("The series snapshot contains duplicate show IDs.")
    return frame.sort_values("movie_id").reset_index(drop=True), document.get("fetched_utc")
