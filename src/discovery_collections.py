"""Transparent discovery shelves. No historical votes are called 'trending'."""

from datetime import date, timedelta

import numpy as np


def collections(view, profile=None, excluded=(), today=None, limit=12):
    today = today or date.today()
    profile = view.validate_profile(profile or {})
    excluded = set(excluded) | set(profile)
    eligible = set(view.rows) - excluded
    recent, upcoming, tonight = [], [], []
    for mid, title in view.titles.items():
        if mid not in eligible:
            continue
        release = date.fromisoformat(title.release_date) if title.release_date else None
        if release and today - timedelta(days=730) <= release <= today:
            recent.append((release, mid))
        elif release and today < release <= today + timedelta(days=180):
            upcoming.append((release, mid))
        if (
            title.media_type == "Movie"
            and title.runtime is not None
            and title.runtime <= 130
            and release
            and release <= today
        ):
            tonight.append(mid)
    popular, gems = [], []
    if view.base is not None:
        engine = view.base
        counts = engine.popularity.counts[: engine.film_count]
        nonzero = counts[counts >= 5]
        low_reach = float(np.median(nonzero)) if len(nonzero) else 0
        for i, mid in enumerate(engine.movie_ids[: engine.film_count]):
            mid = int(mid)
            if mid not in eligible:
                continue
            count, average = int(counts[i]), float(engine.popularity.averages[i])
            if count:
                popular.append((count, mid))
            if 5 <= count <= low_reach and average >= 4:
                gems.append((average, count, mid))
    seed, similar = None, []
    liked = [mid for mid, value in profile.items() if value >= 4]
    if liked and view.content is not None:
        seed = min(liked, key=lambda mid: (-profile[mid], mid))
        similarities = view.content.features @ view.content.features[view.positions[seed]]
        similar = [
            mid
            for mid in sorted(eligible, key=lambda mid: (-similarities[view.positions[mid]], mid))
            if similarities[view.positions[mid]] > 0
        ][:limit]
    return {
        "recent": [mid for _, mid in sorted(recent, key=lambda row: (-row[0].toordinal(), row[1]))][
            :limit
        ],
        "upcoming": [mid for _, mid in sorted(upcoming)][:limit],
        "popular": [mid for _, mid in sorted(popular, key=lambda row: (-row[0], row[1]))][:limit],
        "hidden_gems": [
            mid for _, _, mid in sorted(gems, key=lambda row: (-row[0], row[1], row[2]))
        ][:limit],
        "tonight": sorted(tonight)[:limit],
        "because_liked": similar,
        "seed": seed,
    }
