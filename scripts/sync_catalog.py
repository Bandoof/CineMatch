"""Explicit modern metadata refresh. Never train models or read personal profiles."""

import argparse
import json
from pathlib import Path

from src.data import ROOT
from src.modern_catalog import ModernCatalog
from src.providers import JsonCache, ProviderClient, provider_search, refresh_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "data" / "discovery")
    parser.add_argument("--pages", type=int, default=3, help="1–20 TVmaze index pages")
    parser.add_argument("--search", help="Optional title query; explicitly sent to providers")
    parser.add_argument("--offline", action="store_true", help="Use response cache only")
    args = parser.parse_args()
    if not 1 <= args.pages <= 20:
        parser.error("Choose 1–20 pages.")
    snapshot = args.directory / "catalog.json"
    catalog = ModernCatalog.load(snapshot)
    client = ProviderClient(JsonCache(args.directory / "responses"))
    titles, status = refresh_catalog(client, args.pages, online=not args.offline)
    if args.search:
        extra, search_status = provider_search(client, args.search, online=not args.offline)
        titles.extend(extra)
        status.update({"search " + k: v for k, v in search_status.items()})
    catalog.update(titles)
    catalog.save(snapshot)
    print(
        json.dumps(
            {
                "snapshot": str(snapshot),
                "titles": len(catalog.titles),
                "movies": sum(t.media_type == "Movie" for t in catalog.titles.values()),
                "series": sum(t.media_type == "Series" for t in catalog.titles.values()),
                "statuses": status,
                "requests": client.requests,
                "cache_hits": client.hits,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
