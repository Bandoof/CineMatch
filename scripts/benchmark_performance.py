"""Offline synthetic engineering timings; never a recommendation-quality benchmark.

Run from repository root: OPENBLAS_NUM_THREADS=1 python -m scripts.benchmark_performance
All catalogs, model files and SQLite writes live in a temporary directory.
"""

import argparse
import hashlib
import json
import os
import platform
import statistics
import time
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from app.recommender import Recommender
from app.runtime import load_runtime
from src.collaborative import BiasedMF
from src.data import GENRES, fingerprint, load_app_movies
from src.memory import MemoryStore
from src.ranking import rank_candidates


def median_ms(action, repetitions):
    action()  # Warm numerical imports/cache separately from the measured samples.
    samples = []
    for _ in range(repetitions):
        start = time.perf_counter()
        action()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


def dataset(directory, items):
    rng = np.random.default_rng(20261009)
    rows = []
    for mid in range(1, items + 1):
        genres = rng.choice(len(GENRES), 2, replace=False)
        flags = [int(i in genres) for i in range(len(GENRES))]
        rows.append(
            "|".join(map(str, [mid, f"Synthetic film {mid} (1995)", "01-Jan-1995", "", "", *flags]))
        )
    (directory / "u.item").write_text("\n".join(rows), encoding="latin-1")
    ratings = [
        (uid, int(mid), int(rng.integers(1, 6)), uid * 100 + j)
        for uid in range(1, 101)
        for j, mid in enumerate(rng.choice(np.arange(1, items + 1), 24, replace=False))
    ]
    pd.DataFrame(ratings).to_csv(directory / "u.data", sep="\t", header=False, index=False)
    return load_app_movies(directory)


def benchmark(items=1500, repetitions=30):
    with TemporaryDirectory(prefix="cinematch-performance-") as temporary:
        directory = Path(temporary) / "ml-100k"
        directory.mkdir()
        movies, ratings = dataset(directory, items)
        start = time.perf_counter()
        model = BiasedMF(factors=8, epochs=3).fit(ratings, movies.movie_id.to_numpy())
        fit_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        engine = Recommender(movies, ratings, collaborative=model)
        engine_ms = (time.perf_counter() - start) * 1000
        (directory / "models").mkdir()
        model.save(directory / "models/full.npz", fingerprint(movies, ratings))
        environment = {
            "CINEMATCH_DATA_DIR": str(directory),
            "CINEMATCH_ARTIFACT_ROOT": str(directory),
            "CINEMATCH_SERIES_FILE": str(directory / "absent-series.json"),
            "CINEMATCH_METADATA_FILE": str(directory / "absent-metadata.json"),
            "CINEMATCH_CONTENT_FILE": str(directory / "absent-content.json"),
            "CINEMATCH_PROFILE_DB": str(directory / "isolated.sqlite3"),
            "CINEMATCH_LOCAL_PROFILES": "0",
            "CINEMATCH_AUTOSAVE": "0",
            "CINEMATCH_DEFAULT_LANGUAGE": "en",
            "CINEMATCH_MAINTENANCE": "0",
            "CINEMATCH_MAINTENANCE_FILE": str(directory / "absent-maintenance.flag"),
        }
        previous = {key: os.environ.get(key) for key in environment}
        try:
            os.environ.update(environment)
            from streamlit.testing.v1 import AppTest

            load_runtime.clear()
            start = time.perf_counter()
            app = AppTest.from_file(
                str(Path(__file__).resolve().parents[1] / "app/streamlit_app.py"),
                default_timeout=60,
            ).run()
            startup_ms = (time.perf_counter() - start) * 1000
            if app.exception:
                raise RuntimeError("Synthetic application startup failed.")
            rerun_ms = median_ms(app.run, 5)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            load_runtime.clear()
        profile = {1: 5, 2: 1, 3: 4}
        results, timings = {}, {}
        for algorithm in ("Adaptive", "Hybrid", "Content-based"):

            def action():
                return engine.recommend(profile, algorithm, min_ratings=0, diversity=0.5)

            timings[algorithm] = median_ms(action, repetitions)
            results[algorithm] = [asdict(row) for row in action()]
        rng = np.random.default_rng(42)
        features = rng.random((10000, 19))
        features /= np.linalg.norm(features, axis=1, keepdims=True)
        scores = rng.random(10000)
        indices = np.arange(10000)

        def mmr():
            return rank_candidates(scores, indices, indices, features, 10, 0.5)

        mmr_ms = median_ms(mmr, repetitions)
        tracemalloc.start()
        mmr()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        store = MemoryStore(directory / "timing.sqlite3")
        store.read()
        document = {"version": 1, "enabled": False, "profile": "", "preferences": {}}
        revision = 0

        def save():
            nonlocal revision
            revision = store.write(document, revision)

        sqlite_ms = median_ms(save, repetitions)
        try:
            import resource

            rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (
                1024 if platform.system() == "Linux" else 1024 * 1024
            )
        except ImportError:
            rss_mib = None
        return {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "blas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
            "items": items,
            "users": 100,
            "events": len(ratings),
            "repetitions": repetitions,
            "model_factors": 8,
            "model_epochs": 3,
            "fit_ms": fit_ms,
            "engine_init_ms": engine_ms,
            "app_cold_ms": startup_ms,
            "app_warm_rerun_ms": rerun_ms,
            "recommend_median_ms": timings,
            "mmr_10000_median_ms": mmr_ms,
            "mmr_peak_allocated_bytes": peak,
            "sqlite_write_median_ms": sqlite_ms,
            "process_peak_rss_mib": rss_mib,
            "output_sha256": hashlib.sha256(
                json.dumps(results, sort_keys=True).encode()
            ).hexdigest(),
            "scope": "Synthetic engineering fixture; not live latency or ML quality.",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, default=1500)
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 24 <= args.items <= 20000 or not 1 <= args.repetitions <= 1000:
        parser.error("Use 24–20000 items and 1–1000 repetitions.")
    result = json.dumps(benchmark(args.items, args.repetitions), indent=2)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
