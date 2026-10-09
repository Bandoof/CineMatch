"""Offline research boundaries. Never loads app models, profiles or SQLite."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.catalog import latest_ratings
from src.evaluation import bootstrap_intervals, ranking_metrics


def digest_json(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_new_json(path, document):
    """Exclusive creation: never replaces historical or previously inspected evidence."""
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


@dataclass
class TargetUser:
    user_id: int
    history: pd.DataFrame
    relevant: set[int]


def targets(past, future, excluded, maximum, minimum_history=20):
    """Predeclared eligibility; hash order never depends on a model's performance.

    Future positives only establish eligibility and evaluation labels. They never
    enter a profile, background statistics, text fitting or seed selection.
    """
    histories = {
        int(uid): group.sort_values(["timestamp", "movie_id"], kind="stable")
        for uid, group in latest_ratings(past).groupby("user_id")
    }
    users = []
    for uid, group in future.groupby("user_id"):
        uid = int(uid)
        history = histories.get(uid)
        if uid in excluded or history is None or len(history) < minimum_history:
            continue
        relevant = {int(mid) for mid in group.loc[group.rating >= 4, "movie_id"]}
        relevant -= set(history.movie_id)
        if relevant:
            users.append(TargetUser(uid, history, relevant))
    users.sort(
        key=lambda user: hashlib.sha256(
            f"CineMatch-v12-2026-10-09:{user.user_id}".encode()
        ).hexdigest()
    )
    return users[:maximum]


def background(past, reserved_ids):
    result = latest_ratings(past[~past.user_id.isin(reserved_ids)])
    if result.empty:
        raise ValueError("No background interactions remain.")
    if set(result.user_id) & set(reserved_ids):
        raise ValueError("Target-user history leaked into training.")
    return result


def verify_boundaries(train, validation, test, validation_ids, test_ids, old_ids):
    if train.empty or validation.empty or test.empty:
        raise ValueError("Empty temporal partition.")
    if not train.timestamp.max() < validation.timestamp.min():
        raise ValueError("Train/validation temporal leakage.")
    if not validation.timestamp.max() < test.timestamp.min():
        raise ValueError("Validation/test temporal leakage.")
    if set(validation_ids) & set(test_ids):
        raise ValueError("Validation and test users must be disjoint.")
    if (set(validation_ids) | set(test_ids)) & set(old_ids):
        raise ValueError("Previously evaluated target users were reused.")
    if not validation_ids or not test_ids:
        raise ValueError("Both cohorts must be nonempty.")


def candidates(movie_ids, profile):
    return np.flatnonzero(~np.isin(movie_ids, list(profile)))


def summarize(movie_ids, users, profiles, scores, genre_features, counts, full_history=False):
    """Same full catalog and tie rule for every model; no sampled negatives.

    Full-history exclusion is an explicitly labelled diagnostic, not the primary
    incomplete-profile experiment. Unavailable positives stay in denominators.
    """
    if len(users) != len(profiles) or len(users) != len(scores) or not users:
        raise ValueError("Identical nonempty ordered cohorts are required.")
    per_user, recommendations, distances, novelties = [], [], [], []
    probabilities = (counts + 1) / (counts.sum() + len(counts))
    for user, profile, score in zip(users, profiles, scores):
        score = np.asarray(score)
        if score.shape != movie_ids.shape or not np.isfinite(score).all():
            raise ValueError("Scores must be finite and match the catalog.")
        excluded = dict.fromkeys(user.history.movie_id) if full_history else profile
        pool = candidates(movie_ids, excluded)
        order = pool[np.lexsort((movie_ids[pool], -score[pool]))[:10]]
        ids = movie_ids[order].tolist()
        recommendations.append(ids)
        per_user.append(ranking_metrics(ids, user.relevant))
        features = genre_features[order]
        upper = np.triu_indices(len(order), 1)
        distances.append(
            float((1 - features @ features.T)[upper].mean()) if len(order) > 1 else 0.0
        )
        novelties.append(float((-np.log2(probabilities[order])).mean()) if len(order) else 0.0)
    summary = {
        metric + "@10": float(np.mean([row[metric] for row in per_user]))
        for metric in ("precision", "recall", "ndcg")
    }
    summary.update(
        coverage=len({mid for row in recommendations for mid in row}) / len(movie_ids),
        diversity=float(np.mean(distances)),
        novelty_bits=float(np.mean(novelties)),
        evaluated_users=len(users),
    )
    summary["past_seen_fraction@10"] = float(
        np.mean(
            [
                len(set(row) & set(user.history.movie_id)) / 10
                for row, user in zip(recommendations, users)
            ]
        )
    )
    return summary, per_user, recommendations


def paired_summary(per_user, resamples=2000, seed=20261009):
    intervals, differences = bootstrap_intervals(per_user, resamples=resamples, seed=seed)
    return {
        "confidence_95": intervals,
        "paired_ndcg_vs_popularity_95": differences,
        "resamples": resamples,
        "seed": seed,
    }


def source_fingerprint(root, paths):
    return digest_json({path: file_digest(Path(root) / path) for path in sorted(paths)})
