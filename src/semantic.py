"""Auditable local content representations: TF-IDF + trained latent semantic analysis.

Uses actual source summaries, not generated plots. This is not a Transformer.
Evaluation can fit vocabulary/projection on past-supported titles only.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from src.movies import identity_keys


class SemanticContent:
    def __init__(self, movies, document=None, train_ids=None, dimensions=64):
        records = document.get("items", {}) if isinstance(document, dict) else {}
        identities = {}
        for item in records.values():
            if isinstance(item, dict) and isinstance(item.get("original_title"), str):
                for key in identity_keys(item["original_title"]):
                    identities.setdefault(key, []).append(item)
        self.items = {}
        texts = []
        self.ids = movies.movie_id.to_numpy(dtype=int)
        self.positions = {int(mid): i for i, mid in enumerate(self.ids)}
        self.covered = np.zeros(len(movies), dtype=bool)
        for i, row in enumerate(movies.itertuples()):
            item = records.get(str(row.movie_id), {})
            if not isinstance(item, dict) or item.get("original_title") != row.title:
                matches = [item for key in identity_keys(row.title) for item in identities.get(key, [])]
                unique = {json.dumps(item, sort_keys=True): item for item in matches}
                item = next(iter(unique.values())) if len(unique) == 1 else {}
            clean = {key: str(item.get(key, ""))[:1500] for key in ("summary_en", "summary_uk", "title_uk")}
            for key in ("source_url", "source_uk"):
                url = item.get(key, "")
                parsed = urlparse(url) if isinstance(url, str) else None
                clean[key] = url if parsed and parsed.scheme == "https" and parsed.hostname in (
                    "en.wikipedia.org", "uk.wikipedia.org", "www.tvmaze.com") else ""
            runtime = item.get("runtime_minutes")
            clean["runtime_minutes"] = runtime if type(runtime) is int and 0 < runtime < 1000 else None
            self.items[int(row.movie_id)] = clean
            self.covered[i] = bool(clean["summary_en"] or clean["summary_uk"])
            genres = " ".join(g.replace("-", "") for g in row.genres)
            texts.append(f"{row.title} {clean['title_uk']} {genres} {genres} {genres} "
                         f"{clean['summary_en']} {clean['summary_uk']}")
        allowed = set(self.ids) if train_ids is None else set(train_ids)
        fit_indices = np.array([i for i, mid in enumerate(self.ids) if mid in allowed], dtype=int)
        if not len(fit_indices):
            raise ValueError("Content training requires a past-supported catalog.")
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=24000,
                                         sublinear_tf=True, strip_accents="unicode", dtype=np.float32)
        self.vectorizer.fit([texts[i] for i in fit_indices])
        self.tfidf = self.vectorizer.transform(texts).tocsr()
        size = min(dimensions, len(fit_indices)-1, self.tfidf.shape[1]-1)
        self.projection = None
        if size >= 2:
            self.projection = TruncatedSVD(n_components=size, random_state=42, n_iter=5)
            self.projection.fit(self.tfidf[fit_indices])
            self.features = normalize(self.projection.transform(self.tfidf)).astype(np.float32)
        else:
            self.features = self.tfidf
        self.dimensions = size if self.projection is not None else self.tfidf.shape[1]
        self.fingerprint = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()

    @classmethod
    def load(cls, movies, path=None, train_ids=None):
        document = json.loads(Path(path).read_text(encoding="utf-8")) if path and Path(path).exists() else None
        if document is not None and (document.get("schema_version") != 1 or not isinstance(document.get("items"), dict)):
            raise ValueError("Invalid content metadata.")
        return cls(movies, document, train_ids)

    def profile_vector(self, profile):
        pairs = [(self.positions[mid], float(value)-3) for mid, value in profile.items() if mid in self.positions]
        if not pairs:
            return None
        indices, weights = zip(*pairs)
        features = self.features[list(indices)]
        vector = np.asarray(features.T @ np.asarray(weights)).ravel()
        norm = np.linalg.norm(vector)
        return vector / norm if norm > 1e-8 else None

    def scores(self, profile):
        vector = self.profile_vector(profile)
        return None if vector is None else np.asarray(self.features @ vector).ravel()

    def query_scores(self, text):
        vector = self.vectorizer.transform([text])
        if vector.nnz == 0:
            return None
        if self.projection is not None:
            latent = normalize(self.projection.transform(vector))[0]
            return np.asarray(self.features @ latent).ravel()
        return (self.features @ vector.T).toarray().ravel()

    def similar(self, mid):
        feature = self.features[self.positions[mid]]
        return (self.features @ feature.T).toarray().ravel() if sparse.issparse(self.features) else self.features @ feature

    def evidence(self, profile, mid):
        """Observable lexical overlap; latent similarity alone is not a causal explanation."""
        liked = [(seed, value) for seed, value in profile.items() if value >= 4 and seed != mid]
        if not liked:
            return None
        similarities = self.similar(mid)
        seed = max(liked, key=lambda item: float(similarities[self.positions[item[0]]]))[0]
        overlap = self.tfidf[self.positions[mid]].multiply(self.tfidf[self.positions[seed]]).tocoo()
        vocabulary = self.vectorizer.get_feature_names_out()
        order = np.argsort(overlap.data)[::-1]
        terms = [str(vocabulary[overlap.col[j]]) for j in order[:4]]
        return {"seed": seed, "terms": terms, "similarity": float(similarities[self.positions[seed]])}
