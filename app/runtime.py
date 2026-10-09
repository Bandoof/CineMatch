"""Bounded engine cache that observes data, model AND benchmark artifact versions."""

import json
import hashlib
import math
import zipfile
from pathlib import Path

import streamlit as st

from app.recommender import ALGORITHMS, Recommender
from src.collaborative import BiasedMF
from src.data import fingerprint, load_app_movies
from src.series import load_series
from src.metadata import CatalogMetadata
from src.catalog import latest_ratings
from src.semantic import SemanticContent


def valid_v3(document, content_hash):
    try:
        policy = document["selected_policy"]
        expected = {(n, m) for n in (3, 5, 10) for m in ("Popularity", "Collaborative", "Semantic", "Genres", "Adaptive")}
        return (document["protocol_version"] == 3 and document["metadata_sha256"] == content_hash
                and document["dataset"] == "MovieLens 1M" and document["test_users"] > 0
                and type(document["validation_users"]) is int and document["validation_users"] > 0
                and type(document["events"]) is int and document["events"] > 0
                and {(r["seed_ratings"], r["algorithm"]) for r in document["results"]} == expected
                and all(len(document["paired_ndcg_vs_popularity_95"][str(n)]["Adaptive"]) == 2
                        and all(type(v) in (int, float) and math.isfinite(v)
                                for v in document["paired_ndcg_vs_popularity_95"][str(n)]["Adaptive"])
                        for n in (3, 5, 10))
                and set(policy) == {"3", "5", "10"}
                and all(isinstance(w, list) and len(w) == 3
                        and all(type(v) in (float, int) and math.isfinite(v) and v >= 0 for v in w)
                        and math.isclose(sum(w), 1) for w in policy.values())
                and all(all(type(row[key]) in (float, int) and math.isfinite(row[key])
                            for key in ("seed_ratings", "ndcg@10", "recall@10", "coverage"))
                        for row in document["results"]))
    except (KeyError, TypeError, ValueError):
        return False


def artifact_signature(paths):
    signature = []
    for value in paths:
        path = Path(value)
        stat = path.stat() if path.exists() else None
        signature.append((str(path.resolve()), None if stat is None else stat.st_mtime_ns,
                          None if stat is None else stat.st_size))
    return tuple(signature)


def valid_report(document, data_hash):
    """Reject incomplete/corrupt artifacts before the interface reads nested fields."""
    try:
        return (document["fingerprint"] == data_hash and document["protocol_version"] == 2
                and 0 <= document["selected_alpha"] <= 1
                and 0 <= document.get("selected_popularity_weight", 0) <= 1
                and all(set(document["metrics"][model]) >=
                        {"precision@10", "recall@10", "ndcg@10", "coverage", "diversity"}
                        for model in ALGORITHMS if model not in ("Adaptive", "Semantic"))
                and all(len(document["confidence_95"][model]["ndcg@10"]) == 2
                        for model in ALGORITHMS if model not in ("Adaptive", "Semantic"))
                and isinstance(document["test_cohort"]["evaluated_users"], int)
                and isinstance(document["onboarding"]["results"], list)
                and isinstance(document["diversity_analysis"], list))
    except (KeyError, TypeError, ValueError):
        return False


@st.cache_resource(show_spinner=False, max_entries=3)
def load_runtime(directory, series_file, artifact_root, signature, metadata_file=None, content_file=None):
    movies, ratings = load_app_movies(directory)
    data_hash = fingerprint(movies, ratings)
    artifact_root = Path(artifact_root)
    expanded = (movies.movie_id >= 1_000_000).any()
    model_file = artifact_root / "models" / ("expanded.npz" if expanded else "full.npz")
    report_file = artifact_root / "reports" / ("expanded_metrics.json" if expanded else "metrics.json")
    warnings = []
    model, report = None, None
    if model_file.exists():
        try:
            model = BiasedMF.load(model_file, data_hash)
        except (ValueError, OSError, KeyError, zipfile.BadZipFile):
            warnings.append("model_rebuilt")
    if report_file.exists():
        try:
            loaded = json.loads(report_file.read_text(encoding="utf-8"))
            if valid_report(loaded, data_hash):
                report = loaded
            else:
                warnings.append("benchmark_stale")
        except (ValueError, OSError):
            warnings.append("benchmark_invalid")
    try:
        series, fetched = load_series(series_file)
    except (ValueError, OSError, KeyError, TypeError):
        series, fetched = None, None
        warnings.append("series_invalid")
    alpha = report["selected_alpha"] if report else .75
    if model is None:
        settings = report.get("model", {}) if report else {}
        parameters = {key: settings[key] for key in ("factors", "regularization") if key in settings}
        model = BiasedMF(**parameters).fit(latest_ratings(ratings), movies.movie_id.to_numpy())
    engine = Recommender(movies, ratings, collaborative=model, alpha=alpha, series=series,
                         popularity_weight=report.get("selected_popularity_weight", 0) if report else 0)
    if metadata_file:
        try:
            engine.metadata = CatalogMetadata.load(engine.movies, metadata_file)
        except (ValueError, OSError, TypeError):
            warnings.append("metadata_invalid")
    engine.ml_report = None
    if content_file and Path(content_file).exists():
        try:
            semantic = SemanticContent.load(engine.movies, content_file)
            engine.attach_content(semantic)
            v3_file = artifact_root / "reports" / "ml_v3.json"
            if v3_file.exists():
                document = json.loads(v3_file.read_text(encoding="utf-8"))
                digest = hashlib.sha256(Path(content_file).read_bytes()).hexdigest()
                if valid_v3(document, digest):
                    engine.attach_content(semantic, document["selected_policy"])
                    engine.ml_report = document
                else:
                    warnings.append("ml_stale")
        except (OSError, ValueError, TypeError, KeyError):
            warnings.append("metadata_invalid")
    return engine, report, fetched, warnings
