"""Optional bounded provider access. No profiles, ratings or credentials enter caches."""

import hashlib
import json
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.modern_catalog import CatalogTitle, clean_text, valid_date

MAX_RESPONSE_BYTES = 4_000_000
CACHE_TTL = 6 * 3600
STALE_LIMIT = 14 * 86400
TMDB_GENRES = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Sci-Fi",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
    10759: "Action",
    10765: "Sci-Fi",
    10768: "War",
    10762: "Children's",
}


@dataclass(frozen=True)
class FetchResult:
    payload: object | None
    status: str
    fetched_at: float | None = None


class JsonCache:
    """At most 100 files / 100 MB; no raw queries or keys in filenames."""

    def __init__(self, directory, max_entries=100):
        self.directory = Path(directory)
        self.max_entries = max_entries
        if not 1 <= max_entries <= 100:
            raise ValueError("Invalid cache capacity.")

    def path(self, key):
        return self.directory / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    def read(self, key, now):
        path = self.path(key)
        try:
            if path.stat().st_size > MAX_RESPONSE_BYTES + 1000:
                return None
            record = json.loads(path.read_text(encoding="utf-8"))
            age = now - record["fetched"]
            if type(record["fetched"]) not in (float, int) or not 0 <= age <= STALE_LIMIT:
                return None
            return record["payload"], age
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            return None

    def write(self, key, payload, now):
        encoded = json.dumps({"fetched": now, "payload": payload}, ensure_ascii=False)
        if len(encoded.encode()) > MAX_RESPONSE_BYTES + 1000:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w", dir=self.directory, encoding="utf-8", delete=False
        ) as temporary:
            temporary.write(encoded)
            pending = Path(temporary.name)
        try:
            pending.replace(self.path(key))
            files = sorted(
                self.directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
            )
            total = 0
            for i, path in enumerate(files):
                total += path.stat().st_size
                if (
                    i >= self.max_entries
                    or total > 100_000_000
                    or now - path.stat().st_mtime > STALE_LIMIT
                ):
                    path.unlink(missing_ok=True)
        finally:
            pending.unlink(missing_ok=True)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credentials to a redirected host.


def http_json(url, headers):
    context = ssl.create_default_context()  # Preserve system proxy CA trust.
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
    request = urllib.request.Request(url, headers=headers)
    with opener.open(request, timeout=8) as response:
        if response.headers.get_content_type() != "application/json":
            raise ValueError("Expected a JSON provider response.")
        content = response.read(MAX_RESPONSE_BYTES + 1)
    if len(content) > MAX_RESPONSE_BYTES:
        raise ValueError("Provider response exceeded its limit.")
    return json.loads(
        content, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON"))
    )


class ProviderClient:
    def __init__(self, cache, token=None, transport=http_json, clock=time.time, sleep=time.sleep):
        self.cache = cache
        self.token = token if token is not None else os.environ.get("TMDB_READ_ACCESS_TOKEN", "")
        self.transport, self.clock, self.sleep = transport, clock, sleep
        self._lock = threading.Lock()
        self._last_request = 0.0
        self._cooldown = {}
        self.hits, self.requests = 0, 0

    def fetch(self, provider, endpoint, params=None, online=False):
        patterns = {
            "TVmaze": r"/(shows(?:/\d+(?:/crew)?)?|search/shows|schedule/web|schedule)",
            "TMDB": r"/(movie/(now_playing|upcoming|\d+)|tv/\d+|search/(movie|tv))",
            "Wikidata": r"/w/api\.php",
        }
        if provider not in patterns or not re.fullmatch(patterns[provider], endpoint):
            raise ValueError("Unsupported provider endpoint.")
        params = dict(params or {})
        if not set(params) <= {
            "q",
            "query",
            "page",
            "date",
            "country",
            "language",
            "include_adult",
            "append_to_response",
            "embed",
            "action",
            "ids",
            "props",
            "languages",
            "format",
        }:
            raise ValueError("Unsupported request parameters.")
        if any(
            not isinstance(v, (str, int)) or isinstance(v, bool) or len(str(v)) > 300
            for v in params.values()
        ):
            raise ValueError("Invalid request parameters.")
        if provider == "Wikidata" and (
            params.get("action") != "wbgetentities"
            or params.get("format") != "json"
            or params.get("props") not in ("labels", "labels|descriptions|claims")
            or params.get("languages") != "uk|en"
            or not re.fullmatch(
                r"Q[1-9]\d{0,8}(?:\|Q[1-9]\d{0,8}){0,19}", str(params.get("ids", ""))
            )
            or set(params) != {"action", "ids", "props", "languages", "format"}
        ):
            raise ValueError("Unsupported Wikidata read operation.")
        query = urllib.parse.urlencode(sorted(params.items()))
        key = f"{provider}:{endpoint}?{query}"
        now = self.clock()
        cached = self.cache.read(key, now)
        if cached and cached[1] <= CACHE_TTL:
            self.hits += 1
            return FetchResult(cached[0], "cache", now - cached[1])
        fallback = cached[0] if cached else None
        fetched_at = now - cached[1] if cached else None
        if not online:
            return FetchResult(fallback, "stale" if cached else "offline", fetched_at)
        if provider == "TMDB" and not self.token:
            return FetchResult(fallback, "stale" if cached else "missing_credentials", fetched_at)
        if now < self._cooldown.get(provider, 0):
            return FetchResult(fallback, "stale" if cached else "rate_limited", fetched_at)
        base = {
            "TVmaze": "https://api.tvmaze.com",
            "TMDB": "https://api.themoviedb.org/3",
            "Wikidata": "https://www.wikidata.org",
        }[provider]
        headers = {
            "User-Agent": "CineMatch/1.4 (https://github.com/Bandoof/CineMatch)",
            "Accept": "application/json",
        }
        if provider == "TMDB":
            headers["Authorization"] = "Bearer " + self.token
        try:
            # Serialize requests and stay below TVmaze's 20 requests / 10 seconds.
            with self._lock:
                delay = (1.0 if provider == "Wikidata" else 0.6) - (
                    self.clock() - self._last_request
                )
                if delay > 0:
                    self.sleep(delay)
                self._last_request = self.clock()
                self.requests += 1
                payload = self.transport(base + endpoint + ("?" + query if query else ""), headers)
            try:
                self.cache.write(key, payload, self.clock())
            except OSError:
                pass  # Read-only storage never prevents using a verified response.
            return FetchResult(payload, "fetched", self.clock())
        except urllib.error.HTTPError as error:
            if error.code == 429:
                retry = error.headers.get("Retry-After", "30") if error.headers else "30"
                try:
                    seconds = max(1, min(120, int(retry)))
                except (ValueError, TypeError):
                    seconds = 30
                self._cooldown[provider] = self.clock() + seconds
                status = "rate_limited"
            else:
                self._cooldown[provider] = self.clock() + 30
                status = "unavailable"
        except (OSError, ValueError, TypeError, RecursionError):
            self._cooldown[provider] = self.clock() + 30
            status = "unavailable"
        # Do not expose exception strings, URLs, authorization or response bodies.
        return FetchResult(fallback, "stale" if cached else status, fetched_at)


class SynopsisText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def synopsis(value):
    parser = SynopsisText()
    parser.feed(value[:20_000] if isinstance(value, str) else "")
    return clean_text(" ".join(parser.parts), 5000)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def parse_tvmaze(show, cast=(), crew=()):
    if not isinstance(show, dict) or show.get("type") not in ("Scripted", "Animation"):
        raise ValueError("Expected a scripted/animated TVmaze show.")
    language = clean_text(show.get("language"))
    summary = synopsis(show.get("summary"))
    image = show.get("image") or {}
    rating = show.get("rating") or {}
    externals = show.get("externals") or {}
    if not all(isinstance(v, dict) for v in (image, rating, externals)):
        raise ValueError("Invalid provider object.")
    genres = show.get("genres") or []
    if not isinstance(genres, list):
        raise ValueError("Invalid provider genres.")
    runtime = show.get("runtime") or show.get("averageRuntime")
    names = tuple(
        clean_text(c.get("person", {}).get("name"), 150)
        for c in cast
        if isinstance(c, dict) and isinstance(c.get("person"), dict)
    )[:20]
    crew_names = tuple(
        clean_text(c["person"].get("name"), 100) + " · " + clean_text(c.get("type"), 40)
        for c in crew
        if isinstance(c, dict)
        and isinstance(c.get("person"), dict)
        and clean_text(c["person"].get("name"), 100)
        and clean_text(c.get("type"), 40)
    )[:10]
    return CatalogTitle(
        provider="TVmaze",
        provider_id=show.get("id"),
        media_type="Series",
        original_title=clean_text(show.get("name")),
        title_en=clean_text(show.get("name")),
        release_date=valid_date(show.get("premiered")),
        genres=tuple(
            "Sci-Fi" if g == "Science-Fiction" else clean_text(g, 80)
            for g in genres[:30]
            if clean_text(g, 80)
        ),
        summary_en=summary if language == "English" else "",
        summary_uk=summary if language == "Ukrainian" else "",
        summary_original=summary,
        poster_url=image.get("medium") or "",
        community_rating=rating.get("average"),
        runtime=runtime,
        cast=tuple(n for n in names if n),
        creators=crew_names,
        imdb_id=externals.get("imdb") or "",
        status=clean_text(show.get("status"), 100),
        fetched_utc=stamp(),
    )


def tmdb_image(path, size="w500"):
    return (
        f"https://image.tmdb.org/t/p/{size}{path}"
        if isinstance(path, str) and re.fullmatch(r"/[A-Za-z0-9_-]+\.(jpg|png|webp)", path)
        else ""
    )


def parse_tmdb(item, media_type="Movie", uk=None):
    if not isinstance(item, dict) or media_type not in ("Movie", "Series"):
        raise ValueError("Invalid TMDB item.")
    uk = (
        uk
        if isinstance(uk, dict) and type(uk.get("id")) is int and uk.get("id") == item.get("id")
        else {}
    )
    title_key, original_key, date_key = (
        ("title", "original_title", "release_date")
        if media_type == "Movie"
        else ("name", "original_name", "first_air_date")
    )
    credits = item.get("credits") or {}
    videos = item.get("videos") or {}
    external = item.get("external_ids") or {}
    if not all(isinstance(v, dict) for v in (credits, videos, external)):
        raise ValueError("Invalid provider details.")
    raw_genres = item.get("genres") or []
    ids = item.get("genre_ids") or []
    if not isinstance(raw_genres, list) or not isinstance(ids, list):
        raise ValueError("Invalid provider genres.")
    genres = tuple(
        clean_text(g.get("name"), 80)
        for g in raw_genres[:30]
        if isinstance(g, dict) and clean_text(g.get("name"), 80)
    )
    genres = genres or tuple(
        TMDB_GENRES[g] for g in ids[:30] if type(g) is int and g in TMDB_GENRES
    )
    genres = tuple("Sci-Fi" if g == "Science Fiction" else g for g in genres)
    cast = credits.get("cast") or []
    crew = credits.get("crew") or []
    if not isinstance(cast, list) or not isinstance(crew, list):
        raise ValueError("Invalid provider credits.")
    cast_names = tuple(
        clean_text(c.get("name"), 150)
        for c in cast[:20]
        if isinstance(c, dict) and clean_text(c.get("name"), 150)
    )
    creators = tuple(
        clean_text(c.get("name"), 150)
        for c in crew
        if isinstance(c, dict) and c.get("job") == "Director" and clean_text(c.get("name"), 150)
    )[:10]
    if media_type == "Series":
        raw = item.get("created_by") or []
        if isinstance(raw, list):
            creators = tuple(
                clean_text(c.get("name"), 150)
                for c in raw[:10]
                if isinstance(c, dict) and clean_text(c.get("name"), 150)
            )
    trailer = ""
    results = videos.get("results") or []
    if isinstance(results, list):
        for video in results:
            if (
                isinstance(video, dict)
                and video.get("official") is True
                and video.get("site") == "YouTube"
                and video.get("type") == "Trailer"
                and isinstance(video.get("key"), str)
                and re.fullmatch(r"[A-Za-z0-9_-]{11}", video["key"])
            ):
                trailer = "https://www.youtube.com/watch?v=" + video["key"]
                break
    vote_count = item.get("vote_count")
    average = item.get("vote_average") if type(vote_count) is int and vote_count > 0 else None
    return CatalogTitle(
        provider="TMDB",
        provider_id=item.get("id"),
        media_type=media_type,
        original_title=clean_text(item.get(original_key) or item.get(title_key)),
        title_en=clean_text(item.get(title_key)),
        title_uk=clean_text(uk.get(title_key)),
        release_date=valid_date(item.get(date_key)),
        genres=genres,
        summary_en=clean_text(item.get("overview"), 5000),
        summary_uk=clean_text(uk.get("overview"), 5000),
        poster_url=tmdb_image(item.get("poster_path")),
        backdrop_url=tmdb_image(item.get("backdrop_path"), "w1280"),
        community_rating=average,
        vote_count=vote_count,
        runtime=item.get("runtime"),
        cast=cast_names,
        creators=creators,
        trailer_url=trailer,
        imdb_id=item.get("imdb_id") or external.get("imdb_id") or "",
        status=clean_text(item.get("status"), 100),
        fetched_utc=stamp(),
        original_language=clean_text(item.get("original_language"), 3),
    )


def dated_title(title, response):
    if response.fetched_at is None:
        return title
    return replace(
        title, fetched_utc=datetime.fromtimestamp(response.fetched_at, timezone.utc).isoformat()
    )


def localized_list(client, endpoint, params, kind, online):
    en = client.fetch("TMDB", endpoint, {**params, "language": "en-US"}, online)
    uk = client.fetch("TMDB", endpoint, {**params, "language": "uk-UA"}, online)
    local = {}
    if isinstance(uk.payload, dict) and isinstance(uk.payload.get("results"), list):
        local = {
            r["id"]: r
            for r in uk.payload["results"][:20]
            if isinstance(r, dict) and type(r.get("id")) is int
        }
    titles = []
    if isinstance(en.payload, dict) and isinstance(en.payload.get("results"), list):
        for item in en.payload["results"][:20]:
            try:
                titles.append(dated_title(parse_tmdb(item, kind, local.get(item.get("id"))), en))
            except (ValueError, TypeError, AttributeError):
                continue
    return titles, en.status


def provider_search(client, query, media_type="All", online=False):
    query = clean_text(query, 160)
    if len(query) < 2:
        return [], {}
    titles, statuses = [], {}
    if media_type in ("All", "Series"):
        response = client.fetch("TVmaze", "/search/shows", {"q": query}, online)
        statuses["TVmaze"] = response.status
        if isinstance(response.payload, list):
            for row in response.payload[:30]:
                try:
                    titles.append(dated_title(parse_tvmaze(row.get("show")), response))
                except (ValueError, TypeError, AttributeError):
                    continue
    for kind in ("Movie", "Series"):
        if media_type not in ("All", kind):
            continue
        path = "movie" if kind == "Movie" else "tv"
        extra, status = localized_list(
            client,
            f"/search/{path}",
            {"query": query, "include_adult": "false", "page": 1},
            kind,
            online,
        )
        statuses["TMDB"] = status
        titles.extend(extra)
    return titles, statuses


def refresh_catalog(client, pages=1, online=False, today=None):
    if not 1 <= pages <= 20:
        raise ValueError("Choose 1–20 TVmaze pages.")
    titles, statuses = [], {}
    for page in range(pages):
        response = client.fetch("TVmaze", "/shows", {"page": page}, online)
        statuses["TVmaze"] = response.status
        if isinstance(response.payload, list):
            for item in response.payload[:250]:
                try:
                    titles.append(dated_title(parse_tvmaze(item), response))
                except (ValueError, TypeError):
                    continue
    day = (today or date.today()).isoformat()
    response = client.fetch("TVmaze", "/schedule/web", {"date": day}, online)
    statuses["TVmaze schedule"] = response.status
    if isinstance(response.payload, list):
        for item in response.payload[:300]:
            try:
                titles.append(
                    dated_title(parse_tvmaze(item.get("_embedded", {}).get("show")), response)
                )
            except (ValueError, TypeError, AttributeError):
                continue
    for endpoint in ("now_playing", "upcoming"):
        extra, status = localized_list(client, f"/movie/{endpoint}", {"page": 1}, "Movie", online)
        statuses["TMDB " + endpoint] = status
        titles.extend(extra)
    return titles, statuses


def title_details(client, title, online=False):
    if title.provider == "Wikidata":
        from src.wikidata_catalog import wikidata_titles

        titles, status = wikidata_titles(
            client, [(f"Q{title.provider_id}", title.media_type)], online
        )
        return (titles[0] if titles else title), status
    if title.provider == "TVmaze":
        response = client.fetch(
            "TVmaze", f"/shows/{title.provider_id}", {"embed": "cast"}, online=online
        )
        crew = client.fetch("TVmaze", f"/shows/{title.provider_id}/crew", online=online)
        if isinstance(response.payload, dict) and response.payload.get("id") == title.provider_id:
            try:
                embedded = response.payload.get("_embedded") or {}
                cast = embedded.get("cast", []) if isinstance(embedded, dict) else []
                return dated_title(
                    parse_tvmaze(
                        response.payload,
                        cast if isinstance(cast, list) else [],
                        crew.payload if isinstance(crew.payload, list) else [],
                    ),
                    response,
                ), response.status
            except (ValueError, TypeError):
                pass
        return title, response.status
    kind = "movie" if title.media_type == "Movie" else "tv"
    path = f"/{kind}/{title.provider_id}"
    en = client.fetch(
        "TMDB",
        path,
        {"language": "en-US", "append_to_response": "credits,videos,external_ids"},
        online,
    )
    uk = client.fetch("TMDB", path, {"language": "uk-UA"}, online)
    if isinstance(en.payload, dict) and en.payload.get("id") == title.provider_id:
        try:
            return dated_title(parse_tmdb(en.payload, title.media_type, uk.payload), en), en.status
        except (ValueError, TypeError):
            pass
    return title, en.status
