"""Identity-checked Wikipedia lead extracts and TVmaze summaries, with attribution."""
import argparse
import html
import json
import re
import time
import urllib.parse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from scripts.download_metadata import fetch
from src.data import ROOT


def save(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def ukrainian_batch(batch, records):
    mapping = {}
    for mid in batch:
        mapping.setdefault(records[mid]["uk_page"], []).append(mid)
    result = fetch("https://uk.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "titles": "|".join(mapping), "prop": "extracts",
        "exintro": 1, "explaintext": 1, "exchars": 1200, "exlimit": 20, "maxlag": 5}))
    if "error" in result:
        raise ValueError("Wikipedia request unavailable; retry the resumable download later.")
    normalized = {row["to"]: row["from"] for row in result.get("query", {}).get("normalized", [])}
    updates = {}
    for page in result.get("query", {}).get("pages", {}).values():
        name = page.get("title")
        for mid in mapping.get(normalized.get(name, name), []):
            updates[mid] = {"summary_uk": str(page.get("extract", ""))[:1400],
                            "source_uk": "https://uk.wikipedia.org/wiki/" + urllib.parse.quote(name)}
    return batch, updates


def download(limit=0):
    metadata = json.loads((ROOT / "data/metadata/catalog.json").read_text(encoding="utf-8"))["items"]
    path = ROOT / "data/metadata/content.json"
    document = (json.loads(path.read_text(encoding="utf-8")) if path.exists() else
                {"schema_version": 1, "items": {}})
    records = document["items"]
    targets = [mid for mid, item in metadata.items() if item.get("page")
               and records.get(mid, {}).get("original_title") != item["original_title"]]
    targets.sort(key=lambda mid: metadata[mid].get("imdb_id") not in
                 {"tt0816692", "tt0468569", "tt1675434", "tt0110413"})
    if limit:
        targets = targets[:limit]
    for start in range(0, len(targets), 20):
        batch = targets[start:start+20]
        mapping = {}
        for mid in batch:
            page = metadata[mid]["page"]
            parsed = urllib.parse.urlparse(page)
            if parsed.hostname != "en.wikipedia.org" or not parsed.path.startswith("/wiki/"):
                continue
            title = urllib.parse.unquote(parsed.path[6:]).replace("_", " ")
            mapping.setdefault(title, []).append(mid)
        result = fetch("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "titles": "|".join(mapping),
            "prop": "extracts|langlinks", "exintro": 1, "explaintext": 1,
            "exchars": 1200, "exlimit": 20, "lllang": "uk", "lllimit": 20, "maxlag": 5}))
        for page in result.get("query", {}).get("pages", {}).values():
            for mid in mapping.get(page.get("title"), []):
                records[mid] = {"original_title": metadata[mid]["original_title"],
                    "summary_en": str(page.get("extract", ""))[:1400],
                    "summary_uk": "", "title_uk": metadata[mid].get("title_uk", ""),
                    "source_url": metadata[mid]["page"], "license": "CC BY-SA; Wikipedia",
                    "uk_page": next((link["*"] for link in page.get("langlinks", []) if link["lang"] == "uk"), "")}
        for mid in batch:
            records.setdefault(mid, {"original_title": metadata[mid]["original_title"], "summary_en": ""})
        document["fetched_utc"] = datetime.now(timezone.utc).isoformat()
        save(path, document)
        print(f"Lead extracts {min(start+20,len(targets))}/{len(targets)}", flush=True)
        time.sleep(.3)
    # Ukrainian summaries are fetched from the linked article, never invented translations.
    uk_targets = [mid for mid, item in records.items() if item.get("uk_page") and not item.get("uk_queried")]
    batches = [uk_targets[start:start+20] for start in range(0, len(uk_targets), 20)]
    # Four bounded workers; only the main thread mutates or writes the corpus.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, (batch, updates) in enumerate(pool.map(lambda b: ukrainian_batch(b, records), batches), 1):
            for mid in batch:
                records[mid].update(updates.get(mid, {}), uk_queried=True)
            save(path, document)
            print(f"Ukrainian extracts {min(index*20,len(uk_targets))}/{len(uk_targets)}", flush=True)
    series_path = ROOT / "data/tvmaze/series.json"
    if series_path.exists():
        for show in json.loads(series_path.read_text(encoding="utf-8"))["shows"]:
            mid = str(-show["id"])
            if mid not in metadata:
                continue
            records.setdefault(mid, {"original_title": metadata[mid]["original_title"]})
            if not records[mid].get("summary_en"):
                records[mid].update(summary_en=html.unescape(re.sub("<[^>]+>", " ", show.get("summary") or ""))[:1400],
                    source_url=show["url"], license="CC BY-SA; TVmaze")
            runtime = show.get("averageRuntime") or show.get("runtime")
            if type(runtime) is int and 0 < runtime < 1000:
                records[mid]["runtime_minutes"] = runtime
    document["fetched_utc"] = datetime.now(timezone.utc).isoformat()
    save(path, document)
    print("Saved content:", len(records), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    download(parser.parse_args().limit)
