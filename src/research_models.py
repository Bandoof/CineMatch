"""Small experimental scorers; production ALS/content formulae remain unchanged."""

import numpy as np
from scipy.stats import rankdata


def fold_in_scores(model, profile, regularization=None):
    """Separate visitor ridge strength from background-training regularization.

    'history_scaled' means lambda=training_lambda*N/10. No missing observations
    are inserted, and the model's fixed item factors/biases are never modified.
    """
    pairs = [
        (model.items[int(mid)], float(value))
        for mid, value in profile.items()
        if int(mid) in model.items
    ]
    if not pairs:
        return model.mean + model.item_bias
    if any(not np.isfinite(value) or not 0.5 <= value <= 5 for _, value in pairs):
        raise ValueError("Invalid observed rating.")
    strength = model.regularization if regularization is None else regularization
    if strength == "history_scaled":
        strength = model.regularization * len(pairs) / 10
    if not isinstance(strength, (int, float)) or not np.isfinite(strength) or strength <= 0:
        raise ValueError("Fold-in regularization must be positive and finite.")
    indices = np.array([index for index, _ in pairs], dtype=int)
    values = np.array([value for _, value in pairs])
    x = np.column_stack([np.ones(len(pairs)), model.item_factors[indices]])
    penalty = np.diag([model.bias_regularization, *([strength] * model.factors)])
    target = values - model.mean - model.item_bias[indices]
    solution = np.linalg.solve(x.T @ x + penalty, x.T @ target)
    return model.mean + solution[0] + model.item_bias + model.item_factors @ solution[1:]


def calibrate(score, pool, kind, mode="fixed"):
    """Comparable scales; percentiles are ranking transforms, not probabilities."""
    score = np.asarray(score)
    if not np.isfinite(score).all() or mode not in ("fixed", "percentile"):
        raise ValueError("Invalid calibration input.")
    if mode == "percentile":
        result = np.full(len(score), 0.5)
        if len(pool) > 1:
            result[pool] = (rankdata(score[pool], method="average") - 1) / (len(pool) - 1)
        return result
    if kind in ("cf", "quality"):
        return (np.clip(score, 1, 5) - 1) / 4
    if kind == "content":
        return (np.clip(score, -1, 1) + 1) / 2
    raise ValueError("Unknown score kind.")


def preference_weights(values, mode):
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or not ((values >= 0.5) & (values <= 5)).all():
        raise ValueError("Only finite observed ratings can form preferences.")
    if mode == "signed":
        return values - 3
    if mode == "positive_only":
        return np.maximum(values - 3, 0)
    if mode == "user_centered":
        return values - values.mean() if len(values) else values
    raise ValueError("Unknown preference model.")


def content_scores(features, positions, profile, mode="signed"):
    pairs = [
        (positions[int(mid)], float(value))
        for mid, value in profile.items()
        if int(mid) in positions
    ]
    if not pairs:
        return None
    indices = np.array([index for index, _ in pairs], dtype=int)
    weights = preference_weights([value for _, value in pairs], mode)
    vector = np.asarray(features[indices].T @ weights).ravel()
    norm = np.linalg.norm(vector)
    return None if norm < 1e-10 else np.asarray(features @ (vector / norm)).ravel()


def content_contributions(features, positions, profile, candidate_id, mode="signed"):
    """Exact additive decomposition of cosine's numerator / observed-profile norm.

    Terms can be negative. This explains this content score, not causation or the
    ALS/blended/MMR ranking. User-centering makes weights depend on the full profile.
    """
    pairs = [
        (int(mid), positions[int(mid)], float(value))
        for mid, value in profile.items()
        if int(mid) in positions
    ]
    if not pairs:
        return []
    weights = preference_weights([value for _, _, value in pairs], mode)
    indices = np.array([index for _, index, _ in pairs], dtype=int)
    vector = np.asarray(features[indices].T @ weights).ravel()
    norm = np.linalg.norm(vector)
    if norm < 1e-10:
        return []
    candidate = features[positions[int(candidate_id)]]
    similarities = features[indices] @ candidate.T
    if hasattr(similarities, "toarray"):
        similarities = similarities.toarray()
    terms = np.asarray(similarities).ravel() * weights / norm
    return [
        {"seed_id": mid, "rating": value, "weight": float(weight), "term": float(term)}
        for (mid, _, value), weight, term in zip(pairs, weights, terms)
    ]
