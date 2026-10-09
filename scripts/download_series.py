"""Download public TVmaze metadata with attribution and bounded rate-limit retries."""

import argparse
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import certifi

from src.data import ROOT
from src.series import parse_show

MODERN = ["Stranger Things", "Severance", "The Last of Us", "Dark", "The Boys",
          "Chernobyl", "Better Call Saul", "The Mandalorian", "Wednesday", "The Bear",
          "Fallout", "House of the Dragon"]


def fetch_json(url):
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "CineMatch/2.0 Portfolio"})
            with urllib.request.urlopen(request, context=context, timeout=30) as response:
                payload = response.read(10_000_001)
            if len(payload) > 10_000_000:
                raise ValueError("Unexpectedly large TVmaze response.")
            return json.loads(payload)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503) or attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("TVmaze request did not complete.")


def download(pages=3):
    if not 1 <= pages <= 20:
        raise ValueError("Choose between 1 and 20 index pages.")
    shows = {}
    for page in range(pages):
        for show in fetch_json(f"https://api.tvmaze.com/shows?page={page}"):
            if parse_show(show) is not None:
                shows[show["id"]] = show
        print(f"Fetched TVmaze page {page}: {len(shows)} scripted/animated series", flush=True)
    for name in MODERN:
        query = urllib.parse.quote(name)
        try:
            show = fetch_json(f"https://api.tvmaze.com/singlesearch/shows?q={query}")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                print(f"No TVmaze match for {name}; skipped", flush=True)
                continue
            raise
        if parse_show(show) is not None:
            shows[show["id"]] = show
    # Keep only needed metadata; descriptions, cast lists and user data are not ingested.
    fields = ("id", "name", "type", "premiered", "genres", "rating", "url", "image", "status", "externals")
    records = [{key: show.get(key) for key in fields} for _, show in sorted(shows.items())]
    destination = ROOT / "data" / "tvmaze" / "series.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": 1, "source": "TVmaze", "source_url": "https://www.tvmaze.com/api",
                "license": "CC BY-SA; see https://www.tvmaze.com/api#licensing",
                "fetched_utc": datetime.now(timezone.utc).isoformat(), "index_pages": pages,
                "additional_searches": MODERN, "shows": records}
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)
    print(f"Saved {len(records)} real series to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=3)
    download(parser.parse_args().pages)
