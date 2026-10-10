"""Consumer catalog facade. The training engine and its scores stay unchanged."""

import math

import numpy as np
import pandas as pd

from src.catalog import integer_id
from src.content_based import ContentBased
from src.modern_catalog import CatalogTitle, ModernCatalog, identity_index, resolve_mapping


class CatalogView:
    def __init__(self, base, catalog=None):
        self.base = base
        self.catalog = catalog or ModernCatalog()
        self.reference_only = set()
        self._rebuild()

    def _rebuild(self):
        self.revision = getattr(self, "revision", 0) + 1
        records = self.base.movies.to_dict("records") if self.base is not None else []
        columns = [
            "movie_id",
            "title",
            "year",
            "genres",
            "media_type",
            "source",
            "aliases",
            "imdb_id",
        ]
        original = self.base.movies if self.base is not None else pd.DataFrame(columns=columns)
        indexed = identity_index(original)
        self.titles, self.mapping_provenance, self.external_ids = {}, {}, {}
        for title in self.catalog.titles.values():
            mid, provenance = resolve_mapping(title, original, indexed)
            self.external_ids[title.external_key] = mid
            self.mapping_provenance[title.external_key] = provenance
            previous = self.titles.get(mid)
            if previous is None or title.title_uk or not previous.title_uk:
                self.titles[mid] = title
        known = set(original.movie_id)
        for mid, title in sorted(self.titles.items()):
            if mid not in known:
                records.append(
                    {
                        "movie_id": mid,
                        "title": title.original_title,
                        "year": title.year,
                        "genres": title.genres or ("unknown",),
                        "media_type": title.media_type,
                        "source": title.provider,
                        "aliases": (mid,),
                        "imdb_id": title.imdb_id,
                    }
                )
        self.movies = pd.DataFrame(records) if records else pd.DataFrame(columns=columns)
        self.rows = {int(row.movie_id): row for row in self.movies.itertuples(index=False)}
        self.positions = {mid: i for i, mid in enumerate(self.rows)}
        self.movie_ids = self.movies.movie_id.to_numpy(dtype=np.int64)
        self.aliases = dict(self.base.aliases) if self.base is not None else {}
        self.aliases.update({mid: mid for mid in self.rows if mid not in known})
        self.content = ContentBased(self.movies) if len(self.movies) else None
        self.reference_only &= set(self.rows)

    def normalize_id(self, value):
        mid = integer_id(value)
        if mid not in self.aliases:
            raise ValueError("Unknown catalog identity.")
        return self.aliases[mid]

    def validate_profile(self, profile):
        if not isinstance(profile, dict):
            raise ValueError("Ratings must be a mapping.")
        checked = {}
        for mid, rating in profile.items():
            mid = self.normalize_id(mid)
            if isinstance(rating, bool):
                raise ValueError("Ratings must be numeric.")
            value = float(rating)
            if not math.isfinite(value) or not 0.5 <= value <= 5:
                raise ValueError("Invalid rating.")
            if mid in checked and checked[mid] != value:
                raise ValueError("Conflicting alias ratings.")
            checked[mid] = value
        return checked

    def display_title(self, mid, language="en"):
        mid = self.normalize_id(mid)
        title = self.titles.get(mid)
        if title:
            name = title.title(language)
            return f"{name} ({title.year})" if title.year else name
        return self.base.display_title(mid, language)

    def add_titles(self, titles):
        titles = list(titles)
        self.catalog.update(titles)
        self.reference_only -= {title.canonical_id for title in titles}
        self._rebuild()

    def known_profile(self, profile):
        checked = self.validate_profile(profile)
        return {
            mid: rating
            for mid, rating in checked.items()
            if self.base is not None and mid in self.base.positions
        }

    def recommend_known(self, profile=None, algorithm="Adaptive", **filters):
        if self.base is None:
            return []
        filters = dict(filters)
        for key in ("blocked", "watched", "topic_blocked", "snoozed"):
            if key in filters and filters[key] is not None:
                filters[key] = {mid for mid in filters[key] if mid in self.base.positions}
        return self.base.recommend(self.known_profile(profile or {}), algorithm, **filters)

    def modern_recommend(self, profile=None, excluded=(), limit=12, genres=(), media_type="All"):
        """Disclosed signed genre affinity / provider quality, never an ALS prediction."""
        if self.content is None:
            return []
        profile = self.validate_profile(profile or {})
        scores = self.content.scores(profile)
        excluded = set(excluded) | set(profile)
        candidates = []
        for mid, title in self.titles.items():
            if (
                mid in excluded
                or (self.base is not None and mid in self.base.positions)
                or (media_type != "All" and title.media_type != media_type)
                or (genres and not set(genres).intersection(title.genres))
            ):
                continue
            affinity = None if scores is None else float(scores[self.positions[mid]])
            quality = None if title.community_rating is None else title.community_rating / 10
            score = (
                0.75 * (affinity + 1) / 2 + 0.25 * quality
                if affinity is not None and quality is not None
                else (affinity + 1) / 2
                if affinity is not None
                else quality
                if quality is not None
                else 0
            )
            candidates.append((mid, score))
        return sorted(candidates, key=lambda row: (-row[1], row[0]))[:limit]

    def export_references(self, identities):
        fields = (
            "provider",
            "provider_id",
            "media_type",
            "original_title",
            "title_en",
            "title_uk",
            "release_date",
            "genres",
        )
        return {
            str(mid): {key: self.titles[mid].to_dict()[key] for key in fields}
            for mid in sorted(identities)
            if mid in self.titles and (self.base is None or mid not in self.base.positions)
        }

    def with_references(self, references):
        if not isinstance(references, dict) or len(references) > 5000:
            raise ValueError("Invalid saved catalog references.")
        catalog = ModernCatalog(self.catalog.titles.values())
        restored = set(self.reference_only)
        for key, record in references.items():
            if not isinstance(record, dict) or set(record) - {
                "provider",
                "provider_id",
                "media_type",
                "original_title",
                "title_en",
                "title_uk",
                "release_date",
                "genres",
            }:
                raise ValueError("Invalid saved identity fields.")
            title = CatalogTitle.from_dict(record)
            mid = integer_id(key)
            if mid != title.canonical_id:
                raise ValueError("Saved provider namespace mismatch.")
            if title.external_key not in catalog.titles:
                catalog.update([title])
                restored.add(mid)
        candidate = CatalogView(self.base, catalog)
        candidate.reference_only = restored
        return candidate

    def adopt_references(self, candidate):
        self.catalog = candidate.catalog
        self.reference_only = candidate.reference_only
        self._rebuild()
