"""Pinned GroupLens 1M benchmark; no demographics or executable models."""
import hashlib
import io
import json
import ssl
import urllib.request
import zipfile
from datetime import datetime, timezone

import certifi
import pandas as pd

from src.data import GENRES, ROOT

URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"


def download():
    destination = ROOT / "data" / "ml-1m"
    destination.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(URL, headers={"User-Agent": "CineMatch/4.0 (https://github.com/Bandoof)"})
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        blob = response.read(20_000_001)
    if len(blob) > 20_000_000:
        raise ValueError("Oversized archive.")
    checksum = hashlib.sha256(blob).hexdigest()
    receipt = destination / "source.json"
    if receipt.exists() and json.loads(receipt.read_text())["sha256"] != checksum:
        raise ValueError("Benchmark changed; refusing to replace the pinned snapshot.")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        for name in ("movies.dat", "ratings.dat", "README"):
            member = archive.getinfo("ml-1m/" + name)
            if member.file_size > 40_000_000:
                raise ValueError("Oversized member.")
        for name in ("movies.dat", "ratings.dat", "README"):
            (destination / name).write_bytes(archive.read("ml-1m/" + name))
    receipt.write_text(json.dumps({"url": URL, "sha256": checksum,
                       "downloaded_utc": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
    print("MovieLens 1M downloaded and pinned:", checksum, flush=True)


def load(directory=None):
    directory = directory or ROOT / "data" / "ml-1m"
    movies = pd.read_csv(directory / "movies.dat", sep="::", engine="python", encoding="latin1",
                         names=["movie_id", "title", "raw_genres"])
    movies["genres"] = movies.raw_genres.map(lambda value: tuple(value.split("|")))
    movies["year"] = pd.to_numeric(movies.title.str.extract(r"\((\d{4})\)$", expand=False),
                                    errors="coerce").fillna(0).astype(int)
    movies = movies.drop(columns="raw_genres")
    for genre in GENRES:
        movies[genre] = movies.genres.map(lambda values: int(genre in values))
    events = pd.read_csv(directory / "ratings.dat", sep="::", engine="python",
                         names=["user_id", "movie_id", "rating", "timestamp"])
    if events.empty or not events.rating.between(1, 5).all() or not set(events.movie_id) <= set(movies.movie_id):
        raise ValueError("Invalid benchmark ratings.")
    return movies, events


if __name__ == "__main__":
    download()
