"""A finite, diverse recognition queue, separate from recommendation ranking."""

import numpy as np


def discovery_queue(engine, profile=None, not_seen=None, blocked=None, media_type="All",
                    localized_only=False, watched=None):
    """Popular/recognisable titles, round-robin across media and genre.

    'Not seen' is only a prompt exclusion. It never becomes a dislike, viewing
    interaction or recommendation exclusion. No user preferences are sent out.
    """
    profile = engine.validate_profile(profile or {})
    excluded = set(profile) | {engine.normalize_id(mid) for mid in (not_seen or [])}
    excluded |= {engine.normalize_id(mid) for mid in (blocked or [])}
    excluded |= {engine.normalize_id(mid) for mid in (watched or [])}
    quality = engine.score_components({})["Popularity"]
    # Recognition needs reach, not just a high mean based on very few votes.
    quality[:engine.film_count] += np.log1p(engine.popularity.counts[:engine.film_count]) * .35
    order = sorted(range(len(engine.movie_ids)), key=lambda i: (-quality[i], int(engine.movie_ids[i])))
    buckets = {}
    for index in order:
        row = engine.rows[int(engine.movie_ids[index])]
        mid = int(row.movie_id)
        if mid in excluded or (media_type != "All" and row.media_type != media_type):
            continue
        if localized_only and not engine.metadata.translated(mid):
            continue
        genre = next((g for g in row.genres if g not in ("Drama", "unknown")), row.genres[0])
        buckets.setdefault((row.media_type, genre), []).append(mid)
    # Alternate films and series even when one catalog is much larger.
    keys = sorted(buckets, key=lambda key: (key[1], key[0]))
    movie_keys = [key for key in keys if key[0] == "Movie"]
    series_keys = [key for key in keys if key[0] == "Series"]
    keys = [key for pair in zip(movie_keys, series_keys) for key in pair]
    keys += movie_keys[len(series_keys):] + series_keys[len(movie_keys):]
    queue = []
    while buckets:
        for key in keys:
            if key not in buckets:
                continue
            queue.append(buckets[key].pop(0))
            if not buckets[key]:
                del buckets[key]
    anchors = ["Interstellar (2014)", "Breaking Bad (2008)", "Dark Knight, The (2008)",
               "Stranger Things (2016)", "Intouchables (2011)", "Dark (2017)",
               "Professional, The (1994)", "Star Wars (1977)", "Toy Story (1995)",
               "Stranger Things (2016)", "Terminator 2: Judgment Day (1991)",
               "Dark (2017)", "Pulp Fiction (1994)", "Severance (2022)",
               "Fargo (1996)", "Game of Thrones (2011)", "Jurassic Park (1993)",
               "Friends (1994)", "Forrest Gump (1994)", "Chernobyl (2019)"]
    priority = {title: i for i, title in enumerate(anchors)}
    first = sorted((mid for mid in queue if engine.rows[mid].title in priority),
                   key=lambda mid: priority[engine.rows[mid].title])
    anchored = set(first)
    queue = first + [mid for mid in queue if mid not in anchored]
    if len(profile) >= 3 and engine.semantic is not None and queue:
        # Recognition first; then probe less-covered themes among 80 familiar
        # candidates. This is an exploration heuristic, not calibrated uncertainty.
        scores = engine.semantic.scores(profile)
        if scores is not None:
            pool = queue[:80]
            prior = engine.content.features[[engine.positions[mid] for mid in profile]]
            genre_overlap = engine.content.features @ prior.T
            coverage = genre_overlap.max(axis=1)
            counts = np.log1p(engine.popularity.counts)
            reach = counts / max(float(counts.max()), 1)
            reach[engine.is_series] = engine.series_quality[engine.is_series]
            def probe(mid):
                i = engine.positions[mid]
                return .45*reach[i] + .35*(1-abs(scores[i])) + .20*(1-coverage[i])
            selected = max(pool, key=probe)
            queue.remove(selected)
            queue.insert(0, selected)
    return queue
