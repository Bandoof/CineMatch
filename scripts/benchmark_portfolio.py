"""Measured real public-pack session resources, not ML-quality evaluation or an SLA."""

import argparse
import json
import os
import platform
import time
from pathlib import Path

from app.recommender import ALGORITHMS, Recommender
from src.catalog_view import CatalogView
from src.discovery_search import SearchIndex, catalog_records
from src.portfolio import initial_profile, prepared_engine, sample_catalog

ROOT = Path(__file__).resolve().parents[1]


def benchmark(pack, sessions=5):
    if not 1 <= sessions <= 8:
        raise ValueError("Choose 1–8 bounded sessions")
    rows, active = [], []
    global_before = Recommender._cached_components.cache_info().currsize
    for _ in range(sessions):
        start = time.perf_counter()
        engine = prepared_engine(pack)
        if engine is None:
            raise ValueError("Prepare a public ML pack first")
        loaded_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        view = CatalogView(engine, sample_catalog(ROOT))
        facade_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        index = SearchIndex(catalog_records(view))
        index_ms = (time.perf_counter() - start) * 1000
        profile = initial_profile(view)
        modes = {}
        for mode in ALGORITHMS:
            start = time.perf_counter()
            results = view.recommend_known(profile["ratings"], mode, min_ratings=0)
            modes[mode] = {"ms": (time.perf_counter() - start) * 1000, "results": len(results)}
            if not results:
                raise ValueError("Public demo mode returned no candidates")
        start = time.perf_counter()
        assert index.search("Інтерстеллар")
        search_ms = (time.perf_counter() - start) * 1000
        active.append(view)  # Measure several simultaneous live session engines.
        rows.append(
            {
                "engine_load_ms": loaded_ms,
                "facade_ms": facade_ms,
                "index_ms": index_ms,
                "uk_search_ms": search_ms,
                "modes": modes,
            }
        )
    if Recommender._cached_components.cache_info().currsize != global_before:
        raise ValueError("Visitor profiles entered the global original LRU")
    rss = None
    if platform.system() == "Linux":
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "blas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
        "sessions": sessions,
        "training_items": len(engine.movies),
        "effective_training_events": len(engine.ratings),
        "catalog_items": len(view.rows),
        "peak_process_rss_mib": rss,
        "measurements": rows,
        "global_profile_cache_growth": 0,
        "scope": "Five bounded real public-pack service sessions, independent engines/caches. Not concurrent server throughput, Windows hardware, ML quality or DoS certification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--sessions", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = benchmark(args.pack, args.sessions)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
