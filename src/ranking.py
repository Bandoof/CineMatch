"""Deterministic maximal marginal relevance, shared by UI and evaluation."""

import numpy as np


def rank_candidates(scores, indices, item_ids, features, k=10, diversity=0):
    if k < 1 or not 0 <= diversity <= 1:
        raise ValueError("K must be positive and diversity must be between 0 and 1.")
    indices = np.asarray(indices, dtype=int)
    order = indices[np.lexsort((item_ids[indices], -scores[indices]))]
    if not diversity or len(order) < 2:
        return order[:k]
    values = scores[order]
    span = float(np.ptp(values))
    relevance = (values - values.min()) / span if span > 1e-12 else np.ones(len(values))
    chosen = []
    available = np.ones(len(order), dtype=bool)
    redundancy = np.zeros(len(order))
    for _ in range(min(k, len(order))):
        mmr = (1 - diversity) * relevance - diversity * redundancy
        mmr[~available] = -np.inf
        picked = int(np.argmax(mmr))  # Stable relevance/movie-ID tie break.
        chosen.append(int(order[picked]))
        available[picked] = False
        redundancy = np.maximum(redundancy, features[order] @ features[order[picked]])
    return np.asarray(chosen, dtype=int)
