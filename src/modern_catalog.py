"""Validated provider metadata, independent of training observations and profiles."""

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from src.metadata import trusted_url

TMDB_MOVIE_OFFSET = 1_000_000_000_000
TMDB_TV_OFFSET = 2_000_000_000_000
WIKIDATA_OFFSET = 3_000_000_000_000
WIKIDATA_TV_OFFSET = 4_000_000_000_000
MAX_PROVIDER_ID = 999_999_999
MAX_TITLES = 5000
IMAGE_HOSTS = {"image.tmdb.org", "static.tvmaze.com", "upload.wikimedia.org", "thumb.wikimedia.org"}


def canonical_provider_id(provider, provider_id, media_type):
    if type(provider_id) is not int or not 0 < provider_id <= MAX_PROVIDER_ID:
        raise ValueError("Invalid provider identity.")
    if provider == "TVmaze" and media_type == "Series":
        return -provider_id  # Preserve the established TVmaze profile namespace.
    if provider == "TMDB" and media_type in ("Movie", "Series"):
        offset = TMDB_MOVIE_OFFSET if media_type == "Movie" else TMDB_TV_OFFSET
        return -offset - provider_id
    if provider == "Wikidata" and media_type in ("Movie", "Series"):
        return -(WIKIDATA_OFFSET if media_type == "Movie" else WIKIDATA_TV_OFFSET) - provider_id
    raise ValueError("Unsupported provider or media type.")


def clean_text(value, limit=300):
    if not isinstance(value, str):
        return ""
    return " ".join("".join(c for c in value if (c >= " " and c != "\x7f") or c == "\n").split())[
        :limit
    ]


def valid_date(value):
    if not value:
        return ""
    try:
        return date.fromisoformat(value).isoformat() if isinstance(value, str) else ""
    except ValueError:
        return ""


@dataclass(frozen=True)
class CatalogTitle:
    provider: str
    provider_id: int
    media_type: str
    original_title: str
    title_en: str = ""
    title_uk: str = ""
    release_date: str = ""
    genres: tuple[str, ...] = ()
    summary_en: str = ""
    summary_uk: str = ""
    poster_url: str = ""
    backdrop_url: str = ""
    community_rating: float | None = None
    vote_count: int | None = None
    runtime: int | None = None
    cast: tuple[str, ...] = ()
    creators: tuple[str, ...] = ()
    trailer_url: str = ""
    imdb_id: str = ""
    status: str = ""
    fetched_utc: str = ""
    alternate_titles: tuple[str, ...] = ()
    summary_original: str = ""
    original_language: str = ""
    short_description_en: str = ""
    short_description_uk: str = ""
    localization_source: str = ""
    release_year: int = 0

    def __post_init__(self):
        canonical_provider_id(self.provider, self.provider_id, self.media_type)
        if not self.original_title or self.original_title != clean_text(self.original_title):
            raise ValueError("Invalid original title.")
        for name, limit in (
            ("title_en", 300),
            ("title_uk", 300),
            ("summary_en", 5000),
            ("summary_uk", 5000),
            ("summary_original", 5000),
            ("status", 100),
            ("short_description_en", 300),
            ("short_description_uk", 300),
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or value != clean_text(value, limit):
                raise ValueError("Invalid metadata text.")
        if self.release_date != valid_date(self.release_date):
            raise ValueError("Invalid release date.")
        if type(self.release_year) is not int or not (
            self.release_year == 0 or 1800 <= self.release_year <= 2200
        ):
            raise ValueError("Invalid release year.")
        if (
            self.release_date
            and self.release_year
            and int(self.release_date[:4]) != self.release_year
        ):
            raise ValueError("Conflicting release year.")
        for name, limit, length in (
            ("genres", 30, 80),
            ("cast", 20, 150),
            ("creators", 10, 150),
            ("alternate_titles", 30, 300),
        ):
            values = getattr(self, name)
            if (
                not isinstance(values, tuple)
                or len(values) > limit
                or any(
                    not isinstance(v, str) or not v or v != clean_text(v, length) for v in values
                )
            ):
                raise ValueError("Invalid metadata list.")
        if self.community_rating is not None and (
            type(self.community_rating) not in (float, int)
            or not math.isfinite(self.community_rating)
            or not 0 <= self.community_rating <= 10
        ):
            raise ValueError("Invalid community rating.")
        if self.vote_count is not None and (
            type(self.vote_count) is not int or not 0 <= self.vote_count <= 1_000_000_000
        ):
            raise ValueError("Invalid vote count.")
        if self.runtime is not None and (
            type(self.runtime) is not int or not 0 < self.runtime < 1000
        ):
            raise ValueError("Invalid runtime.")
        for value in (self.poster_url, self.backdrop_url):
            if value and not trusted_url(value, IMAGE_HOSTS):
                raise ValueError("Untrusted artwork URL.")
        if self.trailer_url and not re.fullmatch(
            r"https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}", self.trailer_url
        ):
            raise ValueError("Invalid trailer URL.")
        if self.imdb_id and not re.fullmatch(r"tt\d{7,10}", self.imdb_id):
            raise ValueError("Invalid IMDb identity.")
        if self.original_language and not re.fullmatch(r"[a-z]{2,3}", self.original_language):
            raise ValueError("Invalid original language.")
        if self.localization_source and not re.fullmatch(
            r"https://www\.wikidata\.org/wiki/Q[1-9]\d{0,8}", self.localization_source
        ):
            raise ValueError("Invalid localization provenance.")
        if self.fetched_utc:
            try:
                stamp = datetime.fromisoformat(self.fetched_utc)
                if stamp.tzinfo is None:
                    raise ValueError("Missing timestamp timezone.")
            except (TypeError, ValueError) as error:
                raise ValueError("Invalid metadata timestamp.") from error

    @property
    def canonical_id(self):
        return canonical_provider_id(self.provider, self.provider_id, self.media_type)

    @property
    def external_key(self):
        return f"{self.provider.lower()}:{self.media_type.lower()}:{self.provider_id}"

    @property
    def year(self):
        return int(self.release_date[:4]) if self.release_date else self.release_year

    @property
    def source_url(self):
        if self.provider == "Wikidata":
            return f"https://www.wikidata.org/wiki/Q{self.provider_id}"
        if self.provider == "TVmaze":
            return f"https://www.tvmaze.com/shows/{self.provider_id}"
        kind = "movie" if self.media_type == "Movie" else "tv"
        return f"https://www.themoviedb.org/{kind}/{self.provider_id}"

    def title(self, language="en"):
        return (self.title_uk if language == "uk" else "") or self.title_en or self.original_title

    def summary(self, language="en"):
        return (
            (self.summary_uk if language == "uk" else "")
            or self.summary_en
            or self.summary_original
        )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, item):
        if not isinstance(item, dict):
            raise ValueError("A catalog record must be an object.")
        values = dict(item)
        for name in ("genres", "cast", "creators", "alternate_titles"):
            if name in values:
                if not isinstance(values[name], (list, tuple)):
                    raise ValueError("Invalid metadata list.")
                values[name] = tuple(values[name])
        try:
            return cls(**values)
        except TypeError as error:
            raise ValueError("Invalid catalog record fields.") from error


class ModernCatalog:
    """A bounded metadata snapshot; no interaction events or model weights."""

    def __init__(self, titles=()):
        self.titles = {}
        self.update(titles)

    def update(self, titles):
        updated = dict(self.titles)
        for title in titles:
            if not isinstance(title, CatalogTitle):
                raise ValueError("Only validated titles can enter the catalog.")
            updated[title.external_key] = title
        if len(updated) > MAX_TITLES:
            raise ValueError("Catalog snapshot exceeds its bounded capacity.")
        self.titles = updated

    @classmethod
    def load(cls, path):
        path = Path(path)
        if not path.exists():
            return cls()
        if path.stat().st_size > 30_000_000:
            raise ValueError("Catalog snapshot is too large.")
        document = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(document, dict)
            or document.get("schema_version") != 1
            or not isinstance(document.get("titles"), list)
        ):
            raise ValueError("Unsupported modern catalog snapshot.")
        if len(document["titles"]) > MAX_TITLES:
            raise ValueError("Catalog snapshot is too large.")
        titles = [CatalogTitle.from_dict(item) for item in document["titles"]]
        if len({t.external_key for t in titles}) != len(titles):
            raise ValueError("Duplicate provider identity in snapshot.")
        return cls(titles)

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "schema_version": 1,
            "saved_utc": datetime.now(timezone.utc).isoformat(),
            "titles": [t.to_dict() for _, t in sorted(self.titles.items())],
        }
        encoded = json.dumps(document, ensure_ascii=False, indent=2)
        if len(encoded.encode("utf-8")) > 30_000_000:
            raise ValueError("Catalog snapshot exceeds its byte limit.")
        # Atomic, same-directory replacement; never touch training or profile files.
        from tempfile import NamedTemporaryFile

        with NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as temporary:
            temporary.write(encoded)
            temporary_path = Path(temporary.name)
        try:
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)


def identity_index(movies):
    """Build explicit identity evidence once, retaining duplicate ambiguity."""
    provider, imdb = {}, {}
    for row in movies.itertuples(index=False):
        if getattr(row, "source", "") == "TVmaze":
            provider.setdefault(int(row.movie_id), []).append(row.media_type)
        value = getattr(row, "imdb_id", "")
        if isinstance(value, str) and value:
            key = (value, row.media_type, row.year)
            imdb.setdefault(key, []).append(int(row.movie_id))
    return provider, imdb


def resolve_mapping(title, movies, indexed=None):
    """Explicit identity evidence only: provider ID, or unique IMDb + type + year."""
    if indexed is not None:
        provider, imdb = indexed
        if title.provider == "TVmaze" and provider.get(title.canonical_id) == ["Series"]:
            return title.canonical_id, "provider_identity"
        matches = imdb.get((title.imdb_id, title.media_type, title.year), [])
        if title.imdb_id and title.year and len(matches) == 1:
            return matches[0], "unique_imdb_type_year"
        return title.canonical_id, "separate_provider_identity"
    if title.provider == "TVmaze":
        same = movies[(movies.movie_id == title.canonical_id) & (movies.source == "TVmaze")]
        if len(same) == 1 and same.iloc[0].media_type == "Series":
            return title.canonical_id, "provider_identity"
    if title.imdb_id and title.year and "imdb_id" in movies:
        same = movies[
            (movies.imdb_id == title.imdb_id)
            & (movies.media_type == title.media_type)
            & (movies.year == title.year)
        ]
        if len(same) == 1:
            return int(same.iloc[0].movie_id), "unique_imdb_type_year"
    return title.canonical_id, "separate_provider_identity"
