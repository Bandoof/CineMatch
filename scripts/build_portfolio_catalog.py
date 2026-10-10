"""Explicitly rebuild the small real portfolio snapshot; never touch user profiles."""

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.modern_catalog import ModernCatalog
from src.providers import JsonCache, ProviderClient, dated_title, parse_tvmaze
from src.wikidata_catalog import localize_series, wikidata_titles

ROOT = Path(__file__).resolve().parents[1]


def build(output, cache, online=False):
    manifest = json.loads((ROOT / "assets/demo/sources.json").read_text(encoding="utf-8"))
    entries = manifest["titles"]
    client = ProviderClient(
        JsonCache(cache), token=""
    )  # This workflow never uses TMDB credentials.
    wiki, status = wikidata_titles(
        client, [(t["wikidata"], t["media_type"]) for t in entries], online
    )
    identities = {t.source_url.rsplit("/", 1)[-1]: t for t in wiki}
    verified, failures = [], []
    for entry in entries:
        identity = entry["wikidata"]
        title = identities.get(identity)
        if title is None or title.imdb_id != entry["imdb"]:
            failures.append(identity)
            continue
        if entry["media_type"] == "Movie":
            verified.append(title)
        else:
            response = client.fetch(
                "TVmaze", f"/shows/{entry['tvmaze']}", {"embed": "cast"}, online
            )
            if not isinstance(response.payload, dict):
                failures.append(identity)
                continue
            try:
                cast = response.payload.get("_embedded", {}).get("cast", [])
                series = dated_title(parse_tvmaze(response.payload, cast=cast), response)
                if series.provider_id != entry["tvmaze"] or series.imdb_id != entry["imdb"]:
                    raise ValueError("Provider identity mismatch")
                verified.append(localize_series(series, wiki))
            except (ValueError, TypeError, AttributeError):
                failures.append(identity)
    # Never overwrite a good sample with a silently partial/failed refresh.
    if failures:
        raise ValueError(
            f"Snapshot incomplete: {len(failures)} unavailable identities ({status}). Existing output preserved."
        )
    catalog = ModernCatalog(verified)
    catalog.save(output)
    report = {
        "schema_version": 1,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "total": len(verified),
        "movies": sum(t.media_type == "Movie" for t in verified),
        "series": sum(t.media_type == "Series" for t in verified),
        "uk_titles": sum(bool(t.title_uk) for t in verified),
        "uk_short_descriptions": sum(bool(t.short_description_uk) for t in verified),
        "posters": sum(bool(t.poster_url) for t in verified),
        "community_ratings": sum(t.community_rating is not None for t in verified),
        "released_from_2023": sum(t.year >= 2023 for t in verified),
        "recent_730_days": sum(
            bool(t.release_date)
            and date.today() - timedelta(days=730)
            <= date.fromisoformat(t.release_date)
            <= date.today()
            for t in verified
        ),
        "missing_or_ambiguous_release_dates": sum(not t.release_date for t in verified),
        "requests": client.requests,
        "cache_hits": client.hits,
        "sources": [
            "https://www.wikidata.org/wiki/Wikidata:Licensing",
            "https://www.tvmaze.com/api#licensing",
        ],
        "scope": "Small real dated CC0/CC BY-SA metadata selection, not exhaustive coverage or current popularity. No TMDB token or individual training ratings.",
    }
    output.with_name("coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument(
        "--online", action="store_true", help="Allow bounded official provider requests"
    )
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output, args.cache, args.online), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
