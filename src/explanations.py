"""Faithful base-score decomposition; explanations never modify ranking arrays."""

import numpy as np


def adaptive_parts(engine, profile, user_id=None):
    values = engine.score_components(profile, user_id)
    if not profile:
        return {"quality": (np.ones(len(engine.movie_ids)), values["Popularity"])}
    quality = (np.clip(values["Popularity"], 1, 5) - 1) / 4
    cf = (np.clip(values["Collaborative"], 1, 5) - 1) / 4
    name = (
        "genres"
        if engine.semantic is None
        else ("lsa" if engine.semantic.dimensions >= 2 else "tfidf")
    )
    weights = np.tile(np.asarray(engine.adaptive_weights(profile), dtype=float), (len(quality), 1))
    if not any(mid > 0 for mid in profile):
        weights[:] = (0, 0.75, 0.25)
    weights[engine.is_series] = (0, 0.75, 0.25)
    content = None
    if weights[:, 1].any():
        content = (
            engine.semantic.scores(profile)
            if engine.semantic is not None
            else engine.content.scores(profile)
        )
    content_scaled = quality.copy() if content is None else (np.clip(content, -1, 1) + 1) / 2
    quality[engine.is_series] = engine.series_quality[engine.is_series]
    if content is None:
        weights[:, 2] += weights[:, 1]
        weights[:, 1] = 0
    return {
        "cf": (weights[:, 0], weights[:, 0] * cf),
        name: (weights[:, 1], weights[:, 1] * content_scaled),
        "quality": (weights[:, 2], weights[:, 2] * quality),
    }


def cosine_terms(features, positions, profile, candidate_id):
    """All terms sum to signed content cosine, not the ALS/composite/MMR score."""
    pairs = [
        (int(mid), positions[int(mid)], float(rating))
        for mid, rating in profile.items()
        if int(mid) in positions
    ]
    if not pairs:
        return []
    indices = np.asarray([index for _, index, _ in pairs], dtype=int)
    weights = np.asarray([rating - 3 for _, _, rating in pairs])
    vector = np.asarray(features[indices].T @ weights).ravel()
    norm = np.linalg.norm(vector)
    if norm < 1e-10:
        return []
    similarities = features[indices] @ features[positions[int(candidate_id)]].T
    if hasattr(similarities, "toarray"):
        similarities = similarities.toarray()
    terms = np.asarray(similarities).ravel() * weights / norm
    return [
        {"seed_id": mid, "rating": rating, "term": float(term)}
        for (mid, _, rating), term in zip(pairs, terms)
    ]
