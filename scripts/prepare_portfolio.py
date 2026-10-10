"""Build an optional bounded real public-data ML demo pack, never overwrite profiles."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.download_data import download as download_100k
from scripts.download_movies import download as download_latest
from src.collaborative import BiasedMF
from src.data import fingerprint, load_app_movies
from src.portfolio import PUBLIC_ARCHIVES


def prepare(directory):
    directory = Path(directory)
    if directory.exists():
        raise ValueError("Destination exists; choose a new directory. Nothing was overwritten.")
    directory.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="cinematch-public-pack-", dir=directory.parent) as temporary:
        staging = Path(temporary)
        download_100k(staging / "ml-100k")
        download_latest(staging / "ml-latest-small")
        for name, digest in PUBLIC_ARCHIVES.items():
            source = json.loads((staging / name / "source.json").read_text(encoding="utf-8"))
            if source.get("archive_sha256") != digest:
                raise ValueError(
                    "Public archive changed; re-review provenance before preparing a demo."
                )
        movies, ratings = load_app_movies(staging / "ml-100k")
        counts = ratings.movie_id.value_counts()
        selected = list(counts.sort_values(ascending=False, kind="stable").index[:220])
        selected += [50, 174, 118]
        sample = json.loads(
            (Path(__file__).resolve().parents[1] / "assets/demo/catalog.json").read_text(
                encoding="utf-8"
            )
        )
        known_imdb = {t["imdb_id"] for t in sample["titles"] if t["media_type"] == "Movie"}
        selected += movies.loc[movies.imdb_id.isin(known_imdb), "movie_id"].tolist()
        movies = (
            movies[movies.movie_id.isin(set(selected))].sort_values("movie_id").head(250).copy()
        )
        ratings = (
            ratings[ratings.movie_id.isin(set(movies.movie_id))]
            .sort_values(["timestamp", "user_id", "movie_id"])
            .tail(30000)
            .copy()
        )
        # JSON nulls are explicit; no pickle or private research datasets.
        document = {
            "movies": json.loads(movies.to_json(orient="records")),
            "ratings": json.loads(ratings.to_json(orient="records")),
        }
        restored_movies, restored_ratings = (
            pd.DataFrame(document["movies"]),
            pd.DataFrame(document["ratings"]),
        )
        restored_movies["genres"] = restored_movies.genres.map(tuple)
        restored_movies["aliases"] = restored_movies.aliases.map(tuple)
        output = staging / "pack"
        output.mkdir()
        (output / "dataset.json").write_text(
            json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
            encoding="utf-8",
        )
        # Ordinary model defaults, independent demo artifact; no production weights/policy replaced.
        model = BiasedMF().fit(restored_ratings, restored_movies.movie_id.to_numpy())
        model.save(output / "model.npz", fingerprint(restored_movies, restored_ratings))
        manifest = {
            "schema_version": 1,
            "archives": PUBLIC_ARCHIVES,
            "files": {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                for name in ("dataset.json", "model.npz")
            },
            "movies": len(restored_movies),
            "events": len(restored_ratings),
            "scope": "Bounded public development subset. No research holdout, ML-quality claim, owner profile or synthetic training observations.",
        }
        (output / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        output.rename(directory)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("data/portfolio"))
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.directory), indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
