"""Bayesian weighted rating baseline fitted on training ratings only."""

import numpy as np


class Popularity:
    def fit(self, movie_ids, ratings, prior_count=20.0):
        positions = {int(mid): i for i, mid in enumerate(movie_ids)}
        self.counts = np.zeros(len(movie_ids), dtype=int)
        sums = np.zeros(len(movie_ids))
        for row in ratings.itertuples(index=False):
            i = positions[int(row.movie_id)]
            self.counts[i] += 1
            sums[i] += row.rating
        self.mean = float(ratings.rating.mean())
        self.scores = (sums + prior_count * self.mean) / (self.counts + prior_count)
        self.averages = np.divide(sums, self.counts, out=np.zeros_like(sums), where=self.counts > 0)
        return self
