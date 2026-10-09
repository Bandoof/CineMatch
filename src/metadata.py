"""Presentation metadata never changes catalog identity or model features."""

import json
import re
from pathlib import Path
from urllib.parse import urlparse


def trusted_url(value, hosts):
    if (not isinstance(value, str) or "\\" in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        return ""
    try:
        parsed = urlparse(value)
        return value if (parsed.scheme == "https" and parsed.hostname in hosts
                         and parsed.port in (None, 443)
                         and parsed.username is None and parsed.password is None) else ""
    except ValueError:
        return ""


class CatalogMetadata:
    def __init__(self, movies, document=None):
        self.items = {}
        if document is None:
            return
        if (not isinstance(document, dict) or document.get("schema_version") != 1
                or not isinstance(document.get("items"), dict)):
            raise ValueError("Unsupported presentation metadata.")
        for movie in movies.itertuples():
            item = document["items"].get(str(movie.movie_id), {})
            # Reject stale mappings and remake mismatches, rather than relabeling IDs.
            if not isinstance(item, dict) or item.get("original_title") != movie.title:
                continue
            title = item.get("title_uk", "")
            if not isinstance(title, str) or len(title) > 300:
                title = ""
            self.items[int(movie.movie_id)] = {
                "title_uk": title.strip(),
                "search_aliases": [alias for alias in item.get("search_aliases", [])
                                   if isinstance(alias, str) and len(alias) <= 300]
                                   if isinstance(item.get("search_aliases", []), list) else [],
                "poster_url": trusted_url(item.get("poster_url", ""),
                                          {"upload.wikimedia.org", "thumb.wikimedia.org"}),
                "title_source": trusted_url(item.get("title_source", ""), {"www.wikidata.org"}),
                "image_source": trusted_url(item.get("image_source", ""),
                                             {"en.wikipedia.org", "commons.wikimedia.org"})}

    @classmethod
    def load(cls, movies, path):
        path = Path(path)
        return cls(movies, json.loads(path.read_text(encoding="utf-8")) if path.exists() else None)

    def translated(self, movie_id):
        title = self.items.get(int(movie_id), {}).get("title_uk", "")
        # Some Ukrainian Wikidata labels merely repeat the English title.
        # Keep genuinely localized or language-neutral (e.g. 1+1, 1917) names.
        return bool(title and (re.search(r"[А-Яа-яІіЇїЄєҐґ]", title)
                               or not re.search(r"[^\W\d_]", title)))

    def title(self, movie, language="en"):
        title = self.items.get(int(movie.movie_id), {}).get("title_uk", "")
        if language == "uk" and self.translated(movie.movie_id):
            if movie.year:
                # Wikipedia/Wikidata may include '(film, 1960)' disambiguation.
                title = re.sub(rf"\s*\([^()]*\b{movie.year}\s*\)$", "", title).strip()
                return f"{title} ({movie.year})"
            return title
        return str(movie.title)

    def poster(self, movie):
        if movie.media_type == "Series" and movie.poster_url:
            return str(movie.poster_url)
        return self.items.get(int(movie.movie_id), {}).get("poster_url") or str(movie.poster_url)

    def image_source(self, movie):
        if movie.media_type == "Series" and movie.poster_url:
            return movie.source_url
        return self.items.get(int(movie.movie_id), {}).get("image_source", "")
