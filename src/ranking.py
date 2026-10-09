"""Deterministic maximal marginal relevance, shared by UI and evaluation."""

import numpy as np
from numpy.typing import ArrayLike, NDArray


def rank_candidates(
    scores: NDArray[np.float64],
    indices: ArrayLike,
    item_ids: NDArray[np.int_],
    features: NDArray[np.float64],
    k: int = 10,
    diversity: float = 0,
) -> NDArray[np.int_]:
    if k < 1 or not 0 <= diversity <= 1:
        raise ValueError("K must be positive and diversity must be between 0 and 1.")
    candidate_indices: NDArray[np.int_] = np.asarray(indices, dtype=np.int_)
    indices = candidate_indices
    order: NDArray[np.int_] = candidate_indices[np.lexsort((item_ids[indices], -scores[indices]))]
    if not diversity or len(order) < 2:
        return order[:k]
    values = scores[order]
    span = float(np.ptp(values))
    relevance = (values - values.min()) / span if span > 1e-12 else np.ones(len(values))
    chosen: list[int] = []
    available = np.ones(len(order), dtype=bool)
    redundancy = np.zeros(len(order))
    ordered_features = features[order]
    for _ in range(min(k, len(order))):
        mmr = (1 - diversity) * relevance - diversity * redundancy
        mmr[~available] = -np.inf
        picked = int(np.argmax(mmr))  # Stable relevance/movie-ID tie break.
        chosen.append(int(order[picked]))
        available[picked] = False
        redundancy = np.maximum(redundancy, ordered_features @ ordered_features[picked])
    return np.asarray(chosen, dtype=int)
