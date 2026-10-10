"""Reproducible search engineering measurements; synthetic, never ML quality."""

import argparse
import json
import platform
import statistics
import time
from pathlib import Path

from src.discovery_search import SearchIndex, SearchRecord
from src.search import title_matches


def measure(action, repetitions):
    samples = []
    action()
    for _ in range(repetitions):
        start = time.perf_counter()
        action()
        samples.append((time.perf_counter() - start) * 1000)
    return {
        "median_ms": statistics.median(samples),
        "p95_ms": sorted(samples)[max(0, int(len(samples) * 0.95) - 1)],
    }


def benchmark(items=10000, repetitions=20):
    records = [
        SearchRecord(mid, (f"Synthetic catalog story {mid}",), "Movie", 1990 + mid % 35, ("Drama",))
        for mid in range(1, items + 1)
    ]
    records[0] = SearchRecord(1, ("The Last Signal", "Останній сигнал"), "Movie", 2024, ("Drama",))
    start = time.perf_counter()
    index = SearchIndex(records)
    build_ms = (time.perf_counter() - start) * 1000
    results = {}
    for query in (
        "The Last Signal",
        "Останній сигнал",
        "Last Sign",
        "ostannii syhnal",
        "Останній Signal",
        "The Last Singal",
    ):

        def old():
            return [r.item_id for r in records if title_matches(query, *r.titles)]

        def new():
            return [hit.item_id for hit in index.search(query, limit=12)]

        old_ids, new_ids = old(), new()
        results[query] = {
            "legacy": measure(old, repetitions),
            "indexed": measure(new, repetitions),
            "legacy_found_expected": 1 in old_ids,
            "indexed_top1_expected": bool(new_ids) and new_ids[0] == 1,
        }
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "items": items,
        "repetitions": repetitions,
        "index_build_ms": build_ms,
        "queries": results,
        "expected_top1_passes": sum(v["indexed_top1_expected"] for v in results.values()),
        "cases": len(results),
        "scope": "Deterministic synthetic title retrieval; no network, images or scientific evaluation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, default=10000)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.items < 100 or not 5 <= args.repetitions <= 100:
        parser.error("Use at least 100 items and 5–100 repetitions.")
    document = json.dumps(benchmark(args.items, args.repetitions), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(document + "\n", encoding="utf-8")
    print(document)


if __name__ == "__main__":
    main()
