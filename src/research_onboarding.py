"""Retrospective prompt simulation: only real past ratings can be revealed."""

import numpy as np

from src.discovery import discovery_queue


def simulate(engine, user, strategy, counts=(1, 3, 5, 10, 20)):
    history = {int(row.movie_id): float(row.rating) for row in user.history.itertuples()}
    if len(history) < max(counts):
        raise ValueError("Matched users need enough observed past ratings.")
    if strategy == "recent":
        return {
            count: {
                int(row.movie_id): float(row.rating)
                for row in user.history.tail(count).itertuples()
            }
            for count in counts
        }, {count: count for count in counts}
    if strategy not in ("recognition", "familiar", "genre_diverse", "content_diverse"):
        raise ValueError("Unknown onboarding strategy.")
    # Counts and order come from background interactions, never this user's full
    # history/future labels. The oracle only answers the chosen prompt afterward.
    order = engine.movie_ids[np.lexsort((engine.movie_ids, -engine.popularity.counts))].tolist()
    profile, prompted, snapshots, costs = {}, set(), {}, {}
    queue = (
        discovery_queue(engine, media_type="Movie") if strategy == "recognition" else order.copy()
    )
    while len(profile) < max(counts):
        remaining = [mid for mid in queue if mid not in prompted]
        if not remaining:
            raise ValueError("Prompt queue exhausted before matched seed counts.")
        mid = remaining[0]
        if strategy in ("genre_diverse", "content_diverse") and profile:
            matrix = (
                engine.content.features if strategy == "genre_diverse" else engine.semantic.features
            )
            seen = matrix[[engine.positions[key] for key in profile]]
            # The same recognisable first-80 pool for both diversity heuristics.
            pool = remaining[:80]
            similarity = matrix[[engine.positions[key] for key in pool]] @ seen.T
            if hasattr(similarity, "toarray"):
                similarity = similarity.toarray()
            overlap = np.asarray(similarity).max(axis=1)
            mid = pool[int(np.argmin(overlap))]  # Deterministic reach-order ties.
        prompted.add(mid)
        if mid not in history:
            continue  # Missing evidence is neither a dislike nor a rating.
        profile[mid] = history[mid]
        if len(profile) in counts:
            snapshots[len(profile)] = profile.copy()
            costs[len(profile)] = len(prompted)
        if strategy == "recognition" and len(profile) < max(counts):
            queue = discovery_queue(engine, profile, not_seen=prompted, media_type="Movie")
    return snapshots, costs
