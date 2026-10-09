"""IMDb identity joins, Wikidata Ukrainian labels and Wikipedia page images.

Public metadata only; no user ratings leave the computer. Images are linked,
never downloaded or relicensed. Missing translations remain explicitly marked.
"""

import argparse
import io
import json
import re
import ssl
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

import certifi
import pandas as pd

from src.catalog import canonical_catalog
from src.data import ROOT, load_app_movies


def fetch(url, raw=False):
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "CineMatch/3.0 (https://github.com/Bandoof)",
                "Accept": "application/json" if not raw else "application/zip"})
            with urllib.request.urlopen(request, context=context, timeout=45) as response:
                body = response.read(15_000_001)
            if len(body) > 15_000_000:
                raise ValueError("Unexpectedly large metadata response.")
            return body if raw else json.loads(body)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(min(30, int(error.headers.get("Retry-After", 2 ** (attempt + 1)))))
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("Metadata request failed.")


def title_key(title):
    # Dataset IDs differ: join exact titles INCLUDING year, never their movieIds.
    title = unicodedata.normalize("NFKC", title).casefold().strip()
    title = re.sub(r", (the|a|an)(?= \(\d{4}\)$)", "", title)
    title = re.sub(r"^(the|a|an) ", "", title)
    return re.sub(r"[^\w]+", " ", title).strip()


def title_keys(title):
    """Also match primary names when datasets append alternate-language names."""
    primary = re.sub(r"\([^)]*\)(?=.+\(\d{4}\)$)", "", title)
    primary = re.sub(r"\s+", " ", primary)
    return {title_key(title), title_key(primary)}


def save(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": 1, "fetched_utc": datetime.now(timezone.utc).isoformat(),
                "sources": ["https://www.wikidata.org/wiki/Wikidata:Data_access",
                            "https://www.mediawiki.org/wiki/Extension:PageImages",
                            "https://grouplens.org/datasets/movielens/latest/"],
                "items": records}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def update_identity(records, mid, title, imdb):
    """Cached presentation fields belong to one title/IMDb identity only."""
    key = str(mid)
    previous = records.get(key, {})
    if previous.get("original_title") != title or previous.get("imdb_id") != imdb:
        records[key] = {"original_title": title, "imdb_id": imdb}
    else:
        records[key] = previous


def download(batch_size=100):
    movies, ratings = load_app_movies(ROOT / "data" / "ml-100k")
    films, _, _ = canonical_catalog(movies, ratings)
    destination = ROOT / "data" / "metadata" / "catalog.json"
    records = json.loads(destination.read_text(encoding="utf-8"))["items"] if destination.exists() else {}
    blob = fetch("https://files.grouplens.org/datasets/movielens/ml-latest-small.zip", raw=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        latest = pd.read_csv(archive.open("ml-latest-small/movies.csv"))
        links = pd.read_csv(archive.open("ml-latest-small/links.csv"))
    joined = latest.merge(links, on="movieId")
    grouped = {}
    for row in joined.itertuples():
        for key in title_keys(row.title):
            grouped.setdefault(key, set()).add(f"tt{int(row.imdbId):07}")
    aliases = {
        "Star Wars (1977)": "Star Wars: Episode IV - A New Hope (1977)",
        "Empire Strikes Back, The (1980)": "Star Wars: Episode V - The Empire Strikes Back (1980)",
        "Return of the Jedi (1983)": "Star Wars: Episode VI - Return of the Jedi (1983)",
    }
    for row in films.itertuples():
        native_imdb = getattr(row, "imdb_id", "")
        if isinstance(native_imdb, str) and re.fullmatch(r"tt\d+", native_imdb):
            update_identity(records, row.movie_id, row.title, native_imdb)
            continue
        keys = title_keys(aliases.get(row.title, row.title))
        ids = set().union(*(grouped.get(key, set()) for key in keys))
        if len(ids) == 1:
            update_identity(records, row.movie_id, row.title, next(iter(ids)))
    series_path = ROOT / "data" / "tvmaze" / "series.json"
    if series_path.exists():
        for show in json.loads(series_path.read_text(encoding="utf-8"))["shows"]:
            imdb = (show.get("externals") or {}).get("imdb")
            if isinstance(imdb, str) and re.fullmatch(r"tt\d+", imdb):
                year = int((show.get("premiered") or "0000")[:4])
                title = f"{show['name']} ({year})" if year else show["name"]
                update_identity(records, -show["id"], title, imdb)
    targets = [mid for mid, value in records.items() if not value.get("queried")]
    priority = {"tt0110413", "tt0468569", "tt1675434", "tt0816692"}
    targets.sort(key=lambda mid: records[mid]["imdb_id"] not in priority)
    print(f"Identity matches: {len(records)}; querying {len(targets)}", flush=True)
    for start in range(0, len(targets), batch_size):
        batch = targets[start:start + batch_size]
        ids = " ".join(json.dumps(records[mid]["imdb_id"]) for mid in batch)
        query = ('SELECT ?imdb ?item ?uk ?page (GROUP_CONCAT(DISTINCT ?alias;separator="|") AS ?aliases) WHERE { VALUES ?imdb {' + ids + '}'
                 ' ?item wdt:P345 ?imdb . OPTIONAL {?item rdfs:label ?uk FILTER(LANG(?uk)="uk")}'
                 ' OPTIONAL {?item skos:altLabel ?alias FILTER(LANG(?alias) IN ("uk","en"))}'
                 ' OPTIONAL {?page schema:about ?item; schema:isPartOf <https://en.wikipedia.org/>.}}'
                 ' GROUP BY ?imdb ?item ?uk ?page')
        result = fetch("https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
            {"query": query, "format": "json"}))
        matches = {}
        for binding in result["results"]["bindings"]:
            matches.setdefault(binding["imdb"]["value"], []).append(binding)
        for mid in batch:
            value = records[mid]
            rows = matches.get(value["imdb_id"], [])
            entities = {row["item"]["value"] for row in rows}
            if len(entities) == 1:
                for row in rows:
                    value["title_source"] = row["item"]["value"].replace("http:", "https:")
                    if "uk" in row:
                        value["title_uk"] = row["uk"]["value"]
                    if "page" in row:
                        value["page"] = row["page"]["value"]
                    if "aliases" in row:
                        value["search_aliases"] = row["aliases"]["value"].split("|")
            value["queried"] = True
        save(destination, records)
        print(f"Labels {min(start+batch_size,len(targets))}/{len(targets)}; "
              f"Ukrainian: {sum(bool(v.get('title_uk')) for v in records.values())}", flush=True)
        time.sleep(.25)
    targets = [mid for mid, value in records.items() if value.get("page") and not value.get("image_queried")]
    for start in range(0, len(targets), 40):
        batch = targets[start:start + 40]
        title_to_mid = {}
        for mid in batch:
            title = urllib.parse.unquote(urllib.parse.urlparse(records[mid]["page"]).path[6:]).replace("_", " ")
            title_to_mid[title] = mid
        result = fetch("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "titles": "|".join(title_to_mid),
            "prop": "pageimages", "piprop": "thumbnail|name", "pithumbsize": 400,
            "pilicense": "any", "maxlag": 5}))
        if "error" in result:
            raise ValueError("Wikipedia request unavailable; retry the resumable download later.")
        normalized = {row["to"]: row["from"]
                      for row in result.get("query", {}).get("normalized", [])}
        for page in result.get("query", {}).get("pages", {}).values():
            mid = title_to_mid.get(normalized.get(page["title"], page["title"]))
            if mid and "thumbnail" in page:
                records[mid]["poster_url"] = page["thumbnail"]["source"].split("?")[0]
                records[mid]["image_source"] = "https://en.wikipedia.org/wiki/File:" + urllib.parse.quote(page["pageimage"])
            if mid:
                records[mid]["image_queried"] = True
        save(destination, records)
        print(f"Images {min(start+40,len(targets))}/{len(targets)}", flush=True)
        time.sleep(.25)
    print(f"Saved {len(records)} metadata records to {destination}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=100, choices=range(10, 151))
    download(parser.parse_args().batch_size)
