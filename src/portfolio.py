"""Session-owned demonstration state. No SQLite, credentials or provider clients."""

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from types import MethodType

import pandas as pd

from app.recommender import Recommender
from src.collaborative import BiasedMF
from src.data import fingerprint
from src.modern_catalog import ModernCatalog

PUBLIC_ARCHIVES = {
    "ml-100k": "50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229",
    "ml-latest-small": "696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436",
}
SETS = ("blocked", "topic_blocked", "snoozed", "watched", "watchlist", "not_seen")


def enabled(state):
    return state.get("_portfolio_mode", False) or os.environ.get("CINEMATCH_MODE") == "portfolio"


def sample_catalog(root):
    return ModernCatalog.load(Path(root) / "assets/demo/catalog.json")


def prepared_engine(directory):
    """Read only a bounded explicitly prepared public pack; never ambient local data."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        return None
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 5000:
        raise ValueError("Invalid public pack manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("archives") != PUBLIC_ARCHIVES:
        raise ValueError("Unverified public pack provenance")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != {"dataset.json", "model.npz"}:
        raise ValueError("Unexpected public pack files")
    for name, digest in files.items():
        path = directory / name
        if path.is_symlink() or path.stat().st_size > (
            8_000_000 if name == "dataset.json" else 20_000_000
        ):
            raise ValueError("Invalid public pack size")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Public pack integrity mismatch")
    document = json.loads((directory / "dataset.json").read_text(encoding="utf-8"))
    if not isinstance(document, dict) or set(document) != {"movies", "ratings"}:
        raise ValueError("Unexpected public training fields")
    if not 1 <= len(document["movies"]) <= 250 or not 1 <= len(document["ratings"]) <= 30000:
        raise ValueError("Public demo dataset exceeds limits")
    movies, ratings = pd.DataFrame(document["movies"]), pd.DataFrame(document["ratings"])
    movies["genres"] = movies.genres.map(tuple)
    if "aliases" in movies:
        movies["aliases"] = movies.aliases.map(tuple)
    model = BiasedMF.load(directory / "model.npz", fingerprint(movies, ratings))
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
    # Familiar historical IDs come from the pinned public MovieLens catalog.
    if view.base is not None:
        for mid, rating in ((50, 4.5), (174, 4), (118, 1.5)):
            if mid in view.base.positions:
                values["ratings"][mid] = rating
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
