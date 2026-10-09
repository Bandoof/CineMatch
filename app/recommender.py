"""Shared film/series ranking service with honest cold-item fallbacks."""

from dataclasses import dataclass, replace
from functools import lru_cache

import numpy as np
import pandas as pd

from src.catalog import canonical_catalog, integer_id, latest_ratings
from src.collaborative import BiasedMF
from src.content_based import ContentBased
from src.hybrid import blend_scores
from src.item_knn import ItemKNN
from src.i18n import genre_name, tr
from src.popularity import Popularity
from src.metadata import CatalogMetadata
from src.ranking import rank_candidates

ALGORITHMS = ("Adaptive", "Semantic", "Hybrid", "Collaborative", "Item-KNN", "Content-based", "Popularity")


@dataclass(frozen=True)
class Recommendation:
    movie_id: int
    title: str
    year: int
    genres: tuple[str, ...]
    score: float
    reason: str
    rating_count: int
    average_rating: float | None
    media_type: str = "Movie"
    source: str = "MovieLens"
    source_url: str = ""
    poster_url: str = ""
    rating_scale: int = 5
    status: str = ""
    image_source: str = ""


class Recommender:
    def __init__(self, movies, ratings, collaborative=None, alpha=0.75, series=None, popularity_weight=0):
        if not 0 <= alpha <= 1:
            raise ValueError("Hybrid weight must be between zero and one.")
        films, observations, self.aliases = canonical_catalog(movies, ratings)
        self.ratings = latest_ratings(observations)
        self.film_count = len(films)
        parts = [films]
        if series is not None and not series.empty:
            if (series.movie_id >= 0).any() or series.movie_id.duplicated().any():
                raise ValueError("Series require unique negative TVmaze IDs.")
            parts.append(series)
            self.aliases.update({int(mid): int(mid) for mid in series.movie_id})
        self.movies = pd.concat(parts, ignore_index=True)
        for key, default in (("source_url", "https://grouplens.org/datasets/movielens/100k/"),
                             ("poster_url", ""), ("status", "")):
            if key not in self.movies:
                self.movies[key] = default
            self.movies[key] = self.movies[key].fillna(default)
        if "provider_rating" not in self.movies:
            self.movies["provider_rating"] = np.nan
        self.movie_ids = self.movies.movie_id.to_numpy(dtype=int)
        self.rows = {int(row.movie_id): row for row in self.movies.itertuples(index=False)}
        self.positions = {int(mid): i for i, mid in enumerate(self.movie_ids)}
        self.is_series = self.movies.media_type.eq("Series").to_numpy()
        self.popularity = Popularity().fit(self.movie_ids, self.ratings)
        self.content = ContentBased(self.movies)
        film_ids = self.movie_ids[:self.film_count]
        self.collaborative = collaborative or BiasedMF().fit(self.ratings, film_ids)
        if not np.array_equal(self.collaborative.movie_ids, film_ids):
            raise ValueError("Model and canonical film catalog orders differ.")
        self.knn = ItemKNN().fit(self.ratings, film_ids)
        self.series_quality = (pd.to_numeric(self.movies.provider_rating, errors="coerce")
                               .fillna(5).to_numpy(dtype=float) / 10)
        self.alpha = alpha
        if not 0 <= popularity_weight <= 1:
            raise ValueError("Popularity weight must be between zero and one.")
        self.popularity_weight = popularity_weight
        self.metadata = CatalogMetadata(self.movies)
        self.semantic = None
        self.has_learned_policy = False
        self.adaptive_policy = {"3": [0.0, 0.0, 1.0], "5": [0.0, 0.0, 1.0], "10": [0.0, 0.0, 1.0]}

    def attach_content(self, semantic, policy=None):
        if not np.array_equal(semantic.ids, self.movie_ids):
            raise ValueError("Content and catalog orders differ.")
        if policy:
            for key, weights in policy.items():
                if (key not in self.adaptive_policy or not isinstance(weights, (list, tuple))
                        or len(weights) != 3 or any(type(w) not in (int, float) or not np.isfinite(w) or w < 0 for w in weights)
                        or not np.isclose(sum(weights), 1)):
                    raise ValueError("Invalid learned mixing policy.")
            self.adaptive_policy.update(policy)
            self.has_learned_policy = True
        self.semantic = semantic
        self._cached_components.cache_clear()

    def adaptive_weights(self, profile):
        count = len(profile)
        bucket = "3" if count <= 3 else "5" if count <= 7 else "10"
        return self.adaptive_policy[bucket]

    def display_title(self, mid, language="en"):
        return self.metadata.title(self.rows[self.normalize_id(mid)], language)

    def normalize_id(self, value):
        mid = integer_id(value)
        if mid not in self.aliases:
            raise ValueError(f"Unknown catalog ID: {mid}")
        return self.aliases[mid]

    def validate_profile(self, profile):
        if not isinstance(profile, dict):
            raise ValueError("Ratings must be a mapping of catalog IDs to ratings.")
        clean = {}
        for mid, rating in profile.items():
            mid = self.normalize_id(mid)
            if isinstance(rating, bool):
                raise ValueError("Ratings must be numbers, not booleans.")
            rating = float(rating)
            if not np.isfinite(rating) or not .5 <= rating <= 5:
                raise ValueError("Ratings must be finite numbers between 0.5 and 5.")
            if mid in clean and clean[mid] != rating:
                raise ValueError("Conflicting ratings for two aliases of the same film.")
            clean[mid] = rating
        return clean

    def score_components(self, profile, user_id=None):
        profile = self.validate_profile(profile)
        values = self._cached_components(tuple(sorted(profile.items())), user_id,
                                         self.alpha, self.popularity_weight)
        # Callers may add evaluation flags or adjust scores; never alter the cache.
        return {name: value.copy() for name, value in values.items()}

    @lru_cache(maxsize=8)
    def _cached_components(self, profile_items, user_id, _alpha, _popularity_weight):
        profile = dict(profile_items)
        movie_profile = {mid: rating for mid, rating in profile.items() if mid > 0}
        popular = self.popularity.scores.copy()
        popular[self.is_series] = 1 + 4 * self.series_quality[self.is_series]
        if not profile:
            return {algorithm: popular.copy() for algorithm in ALGORITHMS}
        content = self.content.scores(profile)
        content_scores = popular.copy() if content is None else content
        collaborative = popular.copy()
        knn = popular.copy()
        if movie_profile:
            collaborative[:self.film_count] = self.collaborative.scores(movie_profile, user_id)
            knn[:self.film_count] = self.knn.scores(movie_profile, popular[:self.film_count])
        # There are no individual TVmaze viewing interactions in MovieLens.
        # Do not fold TV ratings into zero movie factors or fabricate a KNN history.
        genre_scaled = self.series_quality if content is None else (np.clip(content, -1, 1) + 1) / 2
        series_fallback = .75 * genre_scaled + .25 * self.series_quality
        collaborative[self.is_series] = 1 + 4 * series_fallback[self.is_series]
        knn[self.is_series] = collaborative[self.is_series]
        hybrid = ((np.clip(collaborative, 1, 5) - 1) / 4 if content is None else
                  blend_scores(collaborative, content, self.alpha))
        if not movie_profile and content is not None:
            # The validated movie alpha cannot personalize a series-only history.
            # Use its real genre signals, without fabricating movie interactions.
            film_quality = (np.clip(popular, 1, 5) - 1) / 4
            hybrid[:self.film_count] = (.75 * genre_scaled + .25 * film_quality)[:self.film_count]
        elif movie_profile:
            hybrid = ((1 - self.popularity_weight) * hybrid
                      + self.popularity_weight * (np.clip(popular, 1, 5) - 1) / 4)
        hybrid[self.is_series] = series_fallback[self.is_series]
        semantic = self.semantic.scores(profile) if self.semantic is not None else content
        semantic_scaled = (np.clip(popular, 1, 5)-1)/4 if semantic is None else (np.clip(semantic, -1, 1)+1)/2
        cf_scaled = (np.clip(collaborative, 1, 5)-1)/4
        quality_scaled = (np.clip(popular, 1, 5)-1)/4
        weights = self.adaptive_weights(profile)
        adaptive = weights[0]*cf_scaled + weights[1]*semantic_scaled + weights[2]*quality_scaled
        if not movie_profile:
            adaptive = .75*semantic_scaled + .25*quality_scaled
        adaptive[self.is_series] = (.75*semantic_scaled + .25*self.series_quality)[self.is_series]
        return {"Popularity": popular, "Content-based": content_scores,
                "Collaborative": collaborative, "Item-KNN": knn, "Hybrid": hybrid,
                "Semantic": semantic_scaled, "Adaptive": adaptive}

    def candidate_indices(self, profile=None, blocked=None, genres=None, year_range=None,
                          min_ratings=1, media_type="All", watched=None):
        if media_type not in ("All", "Movie", "Series") or min_ratings < 0:
            raise ValueError("Invalid media type or rating threshold.")
        profile = self.validate_profile(profile or {})
        excluded = set(profile) | {self.normalize_id(mid) for mid in (blocked or [])}
        excluded |= {self.normalize_id(mid) for mid in (watched or [])}
        eligible = (self.popularity.counts >= min_ratings) | self.is_series
        for mid in excluded:
            eligible[self.positions[mid]] = False
        if media_type != "All":
            eligible &= self.movies.media_type.eq(media_type).to_numpy()
        if genres:
            wanted = set(genres)
            eligible &= self.movies.genres.map(lambda g: bool(wanted.intersection(g))).to_numpy()
        if year_range:
            eligible &= self.movies.year.between(*year_range).to_numpy()
        return np.flatnonzero(eligible)

    def recommend(self, profile=None, algorithm="Hybrid", k=10, blocked=None,
                  genres=None, year_range=None, min_ratings=1, user_id=None,
                  media_type="All", diversity=0, language="en", localized_only=False, watched=None,
                  topic_blocked=None, snoozed=None, query=None):
        if algorithm not in ALGORITHMS:
            raise ValueError("Unknown recommendation algorithm.")
        if k < 1:
            raise ValueError("K must be positive.")
        profile = self.validate_profile(profile or {})
        scores = self.score_components(profile, user_id)[algorithm]
        intent_applied = False
        if query and self.semantic is not None:
            intent = self.semantic.query_scores(query)
            if intent is not None:
                span = scores.max()-scores.min()
                normalized = (scores-scores.min())/span if span > 0 else np.zeros_like(scores)
                scores = .25*normalized + .75*(np.clip(intent, -1, 1)+1)/2
                intent_applied = True
        dismissed = {self.normalize_id(mid) for mid in ((blocked or []) if topic_blocked is None else topic_blocked)}
        if dismissed:
            # Weak, bounded feedback distinct from an explicit low star rating.
            negative = self.content.features[[self.positions[mid] for mid in sorted(dismissed)]]
            direction = negative.mean(axis=0)
            penalty = self.content.features @ direction
            # Original scales differ; apply the same max 20% ranking discount.
            scale = 2 if algorithm == "Content-based" and self.content.scores(profile) is not None else 4
            if (algorithm in ("Hybrid", "Adaptive", "Semantic") and profile) or intent_applied:
                scale = 1
            scores = scores - .20 * scale * penalty
            if self.semantic is not None:
                similarity = np.mean([self.semantic.similar(mid) for mid in sorted(dismissed)], axis=0)
                scores -= .10 * scale * np.clip(similarity, 0, 1)
        excluded = set(blocked or []) | set(snoozed or [])
        indices = self.candidate_indices(profile, excluded, genres, year_range, min_ratings,
                                         media_type, watched)
        if localized_only:
            indices = np.array([i for i in indices if self.metadata.translated(self.movie_ids[i])], dtype=int)
        if media_type == "All" and self.is_series[indices].any() and (~self.is_series[indices]).any():
            film_indices, series_indices = indices[~self.is_series[indices]], indices[self.is_series[indices]]
            films_count = min(len(film_indices), (k + 1) // 2)
            series_count = min(len(series_indices), k - films_count)
            films_count = min(len(film_indices), k - series_count)
            films = rank_candidates(scores, film_indices, self.movie_ids, self.content.features, films_count, diversity) if films_count else []
            shows = rank_candidates(scores, series_indices, self.movie_ids, self.content.features, series_count, diversity) if series_count else []
            # Balance sources instead of comparing incompatible community scales.
            order = [item for pair in zip(films, shows) for item in pair]
            order += list(films[len(shows):]) + list(shows[len(films):])
        else:
            order = rank_candidates(scores, indices, self.movie_ids, self.content.features, k, diversity)
        results = [self._result(int(i), float(scores[i]), profile, algorithm, language) for i in order]
        if intent_applied:
            results = [replace(row, reason=tr("reason_query", language)) for row in results]
        return results

    def _result(self, i, score, profile, algorithm, language):
        movie = self.movies.iloc[i]
        counts = int(self.popularity.counts[i])
        reason = tr("reason_movie_pop", language, count=counts)
        if movie.media_type == "Series":
            reason = tr("reason_tv_pop", language)
            if profile and algorithm != "Popularity":
                reason = tr("reason_tv_profile", language)
                if algorithm in ("Collaborative", "Item-KNN", "Hybrid"):
                    reason += " " + tr("reason_tv_fallback", language)
        elif profile and algorithm != "Popularity":
            reason = tr({"Adaptive": "reason_adaptive", "Semantic": "reason_semantic", "Collaborative": "reason_cf", "Item-KNN": "reason_knn",
                         "Hybrid": "reason_hybrid", "Content-based": "reason_content"}[algorithm],
                        language)
            if algorithm == "Adaptive" and not self.has_learned_policy:
                reason = tr("reason_default", language)
            if algorithm == "Semantic" and self.semantic is None:
                reason = tr("reason_text_missing", language)
            if not any(mid > 0 for mid in profile) and algorithm in ("Collaborative", "Item-KNN"):
                reason = tr("reason_no_movie", language)
            elif not any(mid > 0 for mid in profile) and algorithm == "Hybrid":
                reason = tr("reason_series_to_movie", language)
            elif algorithm == "Hybrid" and self.alpha == 1:
                reason = tr("reason_hybrid_quality" if self.popularity_weight else "reason_cf", language)
        content = self.content.scores(profile) if profile else None
        if profile and algorithm in ("Hybrid", "Content-based"):
            liked = [(self.positions[mid], mid) for mid, rating in profile.items() if rating >= 4]
            matches = [(float(self.content.features[i] @ self.content.features[j]), mid)
                       for j, mid in liked]
            if content is not None and matches and max(matches)[0] > 0:
                _, mid = max(matches)
                source = self.movies.iloc[self.positions[mid]]
                shared = sorted(set(source.genres).intersection(movie.genres))
                reason += " " + tr("reason_match", language,
                                   genres=", ".join(genre_name(g, language) for g in shared),
                                   title=self.metadata.title(source, language))
            if content is None and algorithm == "Content-based":
                reason = tr("reason_neutral", language)
        average = movie.provider_rating if movie.media_type == "Series" else self.popularity.averages[i]
        return Recommendation(int(movie.movie_id), self.metadata.title(movie, language), int(movie.year), movie.genres,
                              score, reason, counts, None if pd.isna(average) else float(average),
                              movie.media_type, movie.source, movie.source_url, self.metadata.poster(movie),
                              10 if movie.media_type == "Series" else 5, movie.status,
                              self.metadata.image_source(movie))
