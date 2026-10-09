"""Cosine similarity of binary genre features; signed rating preferences."""

import numpy as np

class ContentBased:
    def __init__(self, movies):
        self.movie_ids = movies.movie_id.to_numpy(dtype=int)
        self.positions = {int(mid): i for i, mid in enumerate(self.movie_ids)}
        self.genre_names = sorted({g for genres in movies.genres for g in genres})
        features = np.asarray([[float(g in genres) for g in self.genre_names]
                               for genres in movies.genres])
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        self.features = np.divide(features, norms, out=np.zeros_like(features), where=norms > 0)

    def scores(self, profile):
        vector = self.preference_vector(profile)
        norm = np.linalg.norm(vector)
        if norm < 1e-10:
            return None
        return self.features @ (vector / norm)

    def preference_vector(self, profile):
        vector = np.zeros(len(self.genre_names))
        for mid, rating in profile.items():
            if int(mid) in self.positions:
                vector += (float(rating) - 3.0) * self.features[self.positions[int(mid)]]
        return vector

    def signals(self, profile, limit=4):
        vector = self.preference_vector(profile)
        positive = sorted([(g, float(v)) for g, v in zip(self.genre_names, vector) if v > .01],
                          key=lambda pair: -pair[1])[:limit]
        negative = sorted([(g, float(v)) for g, v in zip(self.genre_names, vector) if v < -.01],
                          key=lambda pair: pair[1])[:limit]
        return positive, negative

    def diversity(self, indices):
        if len(indices) < 2:
            return 0.0
        features = self.features[indices]
        similarities = features @ features.T
        upper = np.triu_indices(len(indices), 1)
        return float(np.mean(1.0 - similarities[upper]))
