"""Biased matrix factorization via regularized alternating least squares.

SVD-style latent factors, not a dense SVD of a zero-filled rating matrix.
Only observed ratings enter the objective. A new user is folded into fixed
item factors by solving a small ridge regression, without a full retrain.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


class BiasedMF:
    def __init__(self, factors=24, epochs=15, regularization=5.0, bias_regularization=5.0,
                 random_state=42):
        if factors < 1 or epochs < 1 or regularization <= 0 or bias_regularization <= 0:
            raise ValueError("Factors, epochs and regularization must be positive.")
        self.factors = factors
        self.epochs = epochs
        self.regularization = regularization
        self.bias_regularization = bias_regularization
        self.random_state = random_state

    def _solve(self, factors, targets):
        x = np.column_stack([np.ones(len(targets)), factors])
        penalty = np.diag([self.bias_regularization, *([self.regularization] * self.factors)])
        return np.linalg.solve(x.T @ x + penalty, x.T @ targets)

    def fit(self, ratings, movie_ids):
        if ratings.empty:
            raise ValueError("Cannot fit an empty training set.")
        self.movie_ids = np.asarray(movie_ids, dtype=int)
        self.user_ids = np.sort(ratings.user_id.unique()).astype(int)
        self._index()
        self.mean = float(ratings.rating.mean())
        rng = np.random.default_rng(self.random_state)
        self.user_factors = rng.normal(0, 0.1, (len(self.user_ids), self.factors))
        self.item_factors = rng.normal(0, 0.1, (len(self.movie_ids), self.factors))
        self.user_bias = np.zeros(len(self.user_ids))
        self.item_bias = np.zeros(len(self.movie_ids))
        by_user = []
        by_item = [([], []) for _ in self.movie_ids]
        for uid, group in ratings.groupby("user_id", sort=True):
            indices = np.array([self.items[int(mid)] for mid in group.movie_id], dtype=int)
            values = group.rating.to_numpy(dtype=float)
            by_user.append((indices, values))
            u = self.users[int(uid)]
            for i, value in zip(indices, values):
                by_item[i][0].append(u)
                by_item[i][1].append(value)
        by_item = [(np.asarray(u, dtype=int), np.asarray(r, dtype=float)) for u, r in by_item]
        for _ in range(self.epochs):
            for u, (indices, values) in enumerate(by_user):
                solution = self._solve(
                    self.item_factors[indices], values - self.mean - self.item_bias[indices]
                )
                self.user_bias[u], self.user_factors[u] = solution[0], solution[1:]
            for i, (indices, values) in enumerate(by_item):
                if not len(indices):
                    self.item_factors[i] = 0
                    continue
                solution = self._solve(
                    self.user_factors[indices], values - self.mean - self.user_bias[indices]
                )
                self.item_bias[i], self.item_factors[i] = solution[0], solution[1:]
        return self

    def _index(self):
        self.items = {int(mid): i for i, mid in enumerate(self.movie_ids)}
        self.users = {int(uid): i for i, uid in enumerate(self.user_ids)}

    def scores(self, profile=None, user_id=None):
        if user_id in self.users:
            u = self.users[user_id]
            bias, factors = self.user_bias[u], self.user_factors[u]
        elif profile:
            pairs = [(self.items[int(mid)], float(r)) for mid, r in profile.items()
                     if int(mid) in self.items]
            if not pairs:
                return self.mean + self.item_bias
            indices, values = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
            solution = self._solve(
                self.item_factors[indices], values - self.mean - self.item_bias[indices]
            )
            bias, factors = solution[0], solution[1:]
        else:
            return self.mean + self.item_bias
        return self.mean + bias + self.item_bias + self.item_factors @ factors

    def save(self, path: Path, data_hash: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        # No pickle: loaded data are numeric arrays and Unicode strings only.
        np.savez_compressed(
            path, movie_ids=self.movie_ids, user_ids=self.user_ids,
            user_factors=self.user_factors, item_factors=self.item_factors,
            user_bias=self.user_bias, item_bias=self.item_bias, mean=self.mean,
            factors=self.factors, epochs=self.epochs, regularization=self.regularization,
            bias_regularization=self.bias_regularization, random_state=self.random_state,
            data_hash=data_hash, schema_version=1,
        )

    @classmethod
    def load(cls, path: Path, expected_hash: str):
        with np.load(path, allow_pickle=False) as archive:
            if int(archive["schema_version"]) != 1 or str(archive["data_hash"]) != expected_hash:
                raise ValueError("Cached model does not match the training data.")
            model = cls(
                factors=int(archive["factors"]), epochs=int(archive["epochs"]),
                regularization=float(archive["regularization"]),
                bias_regularization=float(archive["bias_regularization"]),
                random_state=int(archive["random_state"]),
            )
            for key in ("movie_ids", "user_ids", "user_factors", "item_factors",
                        "user_bias", "item_bias"):
                setattr(model, key, archive[key].copy())
            model.mean = float(archive["mean"])
            model._index()
            return model
