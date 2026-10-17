"""Session-owned demonstration state. No SQLite, credentials or provider clients."""

import hashlib
import json
import os
import zipfile
from functools import lru_cache
from pathlib import Path
from types import MethodType

import numpy as np
import pandas as pd

from app.recommender import Recommender
from src.collaborative import BiasedMF
from src.data import fingerprint
from src.modern_catalog import ModernCatalog

PUBLIC_ARCHIVES = {
    "ml-latest-small": "696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436",
}
PACK_SCHEMA = 2
PACK_FILES = {"dataset.json": 8_000_000, "model.npz": 20_000_000, "MOVIELENS-LICENSE.txt": 50_000}
SETS = ("blocked", "topic_blocked", "snoozed", "watched", "watchlist", "not_seen")


def enabled(state):
    return state.get("_portfolio_mode", False) or os.environ.get("CINEMATCH_MODE") == "portfolio"


def sample_catalog(root):
    return ModernCatalog.load(Path(root) / "assets/demo/catalog.json")


def prepared_engine(directory):
    """Read only a bounded explicitly prepared public pack; never ambient local data."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if directory.is_symlink():
        raise ValueError("Symlinked public pack directory")
    if not manifest_path.exists():
        return None
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 5000:
        raise ValueError("Invalid public pack manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != PACK_SCHEMA
        or manifest.get("archives") != PUBLIC_ARCHIVES
    ):
        raise ValueError("Unverified public pack provenance")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(PACK_FILES):
        raise ValueError("Unexpected public pack files")
    for name, digest in files.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > PACK_FILES[name]:
            raise ValueError("Invalid public pack size")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Public pack integrity mismatch")
    document = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    if not isinstance(document, dict) or set(document) != {"movies", "ratings"}:
        raise ValueError("Unexpected public training fields")
    if not all(isinstance(document[k], list) for k in ("movies", "ratings")):
        raise ValueError("Invalid public training rows")
    if not 1 <= len(document["movies"]) <= 250 or not 1 <= len(document["ratings"]) <= 30000:
        raise ValueError("Public demo dataset exceeds limits")
    if not all(isinstance(row, dict) for key in document for row in document[key]):
        raise ValueError("Invalid public training rows")
    if not all(
        set(row) == {"user_id", "movie_id", "rating", "timestamp"} for row in document["ratings"]
    ):
        raise ValueError("Unexpected public rating fields")
    movies, ratings = pd.DataFrame(document["movies"]), pd.DataFrame(document["ratings"])
    allowed = {
        "movie_id",
        "title",
        "year",
        "genres",
        "media_type",
        "source",
        "imdb_id",
        "source_url",
        "imdb_url",
        "aliases",
        "alternate_title",
    }
    if not set(movies) <= allowed or not {"movie_id", "title", "year", "genres", "aliases"} <= set(
        movies
    ):
        raise ValueError("Unexpected public movie fields")
    if (
        movies.movie_id.duplicated().any()
        or ratings.duplicated(["user_id", "movie_id"]).any()
        or not set(ratings.movie_id) <= set(movies.movie_id)
        or not np.isfinite(ratings.rating).all()
        or not ratings.rating.between(0.5, 5).all()
    ):
        raise ValueError("Invalid public observations")
    movies["genres"] = movies.genres.map(tuple)
    if "aliases" in movies:
        movies["aliases"] = movies.aliases.map(tuple)
    # Bound decompressed NPZ size before numpy allocates arrays (no pickle).
    try:
        with zipfile.ZipFile(directory / "model.npz") as archive:
            if (
                len(archive.infolist()) > 20
                or sum(m.file_size for m in archive.infolist()) > 20_000_000
            ):
                raise ValueError("Invalid public model archive")
    except zipfile.BadZipFile as error:
        raise ValueError("Invalid public model archive") from error
    model = BiasedMF.load(directory / "model.npz", fingerprint(movies, ratings))
    if (
        model.factors > 24
        or len(model.user_ids) > 610
        or model.item_factors.shape != (len(movies), model.factors)
        or model.user_factors.shape != (len(model.user_ids), model.factors)
        or model.item_bias.shape != (len(movies),)
        or model.user_bias.shape != (len(model.user_ids),)
        or not all(
            np.isfinite(a).all()
            for a in (
                model.item_factors,
                model.user_factors,
                model.item_bias,
                model.user_bias,
                model.mean,
            )
        )
    ):
        raise ValueError("Invalid public model arrays")
    engine = Recommender(movies, ratings, collaborative=model)
    # The original method's class-level LRU retains profile keys globally. Bind
    # its identical underlying formula to an independent per-visitor LRU here.
    engine._cached_components = lru_cache(maxsize=8)(
        MethodType(Recommender._cached_components.__wrapped__, engine)
    )
    return engine


def initial_profile(view):
    """Clearly synthetic preferences on actual identities, not a person's history."""
    values = {"ratings": {}, **{key: set() for key in SETS}, "session_activity": {}}
    preferences = [("tt0111161", 5), ("tt0133093", 4.5), ("tt0816692", 4.5), ("tt17526714", 1.5)]
    for imdb, rating in preferences:
        matches = [mid for mid, t in view.titles.items() if t.imdb_id == imdb]
        if len(matches) == 1:
            values["ratings"][matches[0]] = rating
    # Resolve identities, never reinterpret 100K IDs in a different dataset.
    if view.base is not None:
        examples = {"tt0076759": 4.5, "tt0080684": 4, "tt0116629": 1.5}
        for row in view.base.movies.itertuples():
            if getattr(row, "imdb_id", "") in examples:
                values["ratings"][int(row.movie_id)] = examples[row.imdb_id]
    values["watched"] = set(values["ratings"])
    for mid in view.rows:
        title = view.titles.get(mid)
        if title and title.imdb_id in {"tt3581920", "tt15239678"} and mid not in values["watched"]:
            values["watchlist"].add(mid)
        if title and title.imdb_id == "tt13443470":
            values["watched"].add(mid)
    return values


def reset(state, view, empty=False):
    keep = {
        key: state[key]
        for key in (
            "ui_language",
            "posters",
            "_portfolio_mode",
            "_portfolio_view",
            "_portfolio_pack_error",
        )
        if key in state
    }
    for key in list(state):
        del state[key]
    state.update(keep)
    state.update(
        {"ratings": {}, **{key: set() for key in SETS}, "session_activity": {}}
        if empty
        else initial_profile(view)
    )
    state.update(demo=True, _portfolio_initialized=True)
    if view.base is not None:
        view.base._cached_components.cache_clear()
