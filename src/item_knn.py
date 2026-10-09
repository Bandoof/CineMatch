"""Adjusted cosine on sparse observations; no catalog-square matrix."""

import numpy as np
from scipy.sparse import csr_matrix

from src.catalog import latest_ratings


class ItemKNN:
    def __init__(self, neighbors=40, shrinkage=10):
        self.neighbors = neighbors
        self.shrinkage = shrinkage

    def fit(self, ratings, movie_ids):
        ratings = latest_ratings(ratings)
        self.movie_ids = np.asarray(movie_ids, dtype=int)
        self.positions = {int(mid): i for i, mid in enumerate(self.movie_ids)}
        users = {int(uid): i for i, uid in enumerate(sorted(ratings.user_id.unique()))}
        rows = ratings.user_id.map(users).to_numpy()
        cols = ratings.movie_id.map(self.positions).to_numpy()
        shape = (len(users), len(movie_ids))
        self.mask = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=shape)
        matrix = csr_matrix((ratings.rating.to_numpy(dtype=float), (rows, cols)), shape=shape)
        means = np.asarray(matrix.sum(axis=1)).ravel() / np.maximum(np.asarray(self.mask.sum(axis=1)).ravel(), 1)
        self.centered = csr_matrix((ratings.rating.to_numpy(dtype=float) - means[rows], (rows, cols)), shape=shape)
        self.norms = np.sqrt(np.asarray(self.centered.multiply(self.centered).sum(axis=0)).ravel())
        self.mean = float(ratings.rating.mean())
        return self

    def scores(self, profile, fallback):
        pairs = [(self.positions[int(mid)], float(r)) for mid, r in profile.items()
                 if int(mid) in self.positions]
        scores = np.asarray(fallback, dtype=float).copy()
        if not pairs:
            return scores
        indices = np.asarray([i for i, _ in pairs])
        values = np.asarray([r for _, r in pairs])
        baseline = float(values.mean())
        seeds, seed_mask = self.centered[:, indices], self.mask[:, indices]
        # Bound intermediates even for profiles with thousands of ratings.
        for start in range(0, len(self.movie_ids), 512):
            stop = min(start + 512, len(self.movie_ids))
            products = (self.centered[:, start:stop].T @ seeds).toarray()
            denominator = self.norms[start:stop, None] * self.norms[indices][None, :]
            weights = np.divide(products, denominator, out=np.zeros_like(products), where=denominator > 0)
            common = (self.mask[:, start:stop].T @ seed_mask).toarray()
            weights *= common / (common + self.shrinkage)
            weights = np.maximum(weights, 0)
            for column, index in enumerate(indices):
                if start <= index < stop:
                    weights[index - start, column] = 0
            if len(indices) > self.neighbors:
                order = np.argsort(-weights, axis=1, kind="stable")[:, self.neighbors:]
                np.put_along_axis(weights, order, 0, axis=1)
            total = weights.sum(axis=1)
            scores[start:stop] = np.divide(weights @ (values - baseline), total,
                out=scores[start:stop] - baseline, where=total > 0) + baseline
        return scores
