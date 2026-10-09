"""Full-catalog ranking evaluation with a fixed observation boundary."""

import numpy as np

from app.recommender import ALGORITHMS
from src.hybrid import blend_scores
from src.ranking import rank_candidates


def ranking_metrics(recommended, relevant, k=10):
    relevant = set(relevant)
    if not relevant or k < 1:
        raise ValueError("A positive item and positive K are required.")
    hits = np.asarray([int(mid in relevant) for mid in recommended[:k]])
    discounts = 1 / np.log2(np.arange(len(hits)) + 2)
    ideal = float((1 / np.log2(np.arange(min(k, len(relevant))) + 2)).sum())
    return {"precision": float(hits.sum() / k), "recall": float(hits.sum() / len(relevant)),
            "ndcg": float((hits * discounts).sum() / ideal)}


def prepare_cohort(engine, heldout):
    """Only history from engine.ratings enters profiles; future positives are labels."""
    histories = {int(uid): dict(zip(group.movie_id, group.rating))
                 for uid, group in engine.ratings.groupby("user_id")}
    supported = engine.popularity.counts > 0
    cohort = []
    cold_users = 0
    total_relevant = 0
    unavailable_relevant = 0
    for uid, group in heldout.groupby("user_id"):
        if int(uid) not in histories:
            cold_users += 1
            continue
        profile = histories[int(uid)]
        relevant = set(group.loc[group.rating >= 4, "movie_id"]) - set(profile)
        if not relevant:
            continue
        indices = engine.candidate_indices(profile, media_type="Movie")
        scores = engine.score_components(profile)  # same fold-in as an app visitor
        scores["genre_available"] = engine.content.scores(profile) is not None
        total_relevant += len(relevant)
        unavailable_relevant += sum(not supported[engine.positions[int(m)]] for m in relevant)
        cohort.append((indices, scores, relevant))
    return cohort, {"evaluated_users": len(cohort), "excluded_new_users": cold_users,
                    "heldout_users": int(heldout.user_id.nunique()),
                    "relevant_items": total_relevant,
                    "unavailable_relevant_items": unavailable_relevant,
                    "supported_catalog": int(supported.sum())}


def evaluate_cohort(engine, cohort, algorithm, alpha=None, k=10, diversity=0,
                    return_users=False, popularity_weight=None):
    if not cohort:
        raise ValueError("No warm users with held-out positive ratings.")
    values = []
    recommended_catalog = set()
    diversities = []
    for indices, components, relevant in cohort:
        scores = components[algorithm]
        if algorithm == "Hybrid" and (alpha is not None or popularity_weight is not None):
            # Content-based is popularity only when the genre vector cancels out.
            content = components["Content-based"]
            if not components["genre_available"]:
                scores = (np.clip(components["Collaborative"], 1, 5) - 1) / 4
            else:
                scores = blend_scores(components["Collaborative"], content, engine.alpha if alpha is None else alpha)
            beta = engine.popularity_weight if popularity_weight is None else popularity_weight
            scores = (1 - beta) * scores + beta * (np.clip(components["Popularity"], 1, 5) - 1) / 4
        order = rank_candidates(scores, indices, engine.movie_ids,
                                engine.content.features, k, diversity)
        ids = engine.movie_ids[order].tolist()
        values.append(ranking_metrics(ids, relevant, k))
        recommended_catalog.update(ids)
        diversities.append(engine.content.diversity(order))
    result = {f"{name}@{k}": float(np.mean([v[name] for v in values]))
              for name in ("precision", "recall", "ndcg")}
    result["coverage"] = len(recommended_catalog) / int((engine.popularity.counts > 0).sum())
    result["diversity"] = float(np.mean(diversities))
    return (result, values) if return_users else result


def evaluate_all(engine, heldout, k=10):
    cohort, details = prepare_cohort(engine, heldout)
    return {name: evaluate_cohort(engine, cohort, name, k=k) for name in ALGORITHMS}, details


def bootstrap_intervals(per_user, resamples=1000, seed=42):
    """Paired user resampling: the same user indices are used for every algorithm."""
    sizes = {len(rows) for rows in per_user.values()}
    if len(sizes) != 1 or not sizes or min(sizes) < 1:
        raise ValueError("All models need the same nonempty ordered user cohort.")
    draws = np.random.default_rng(seed).integers(0, min(sizes), (resamples, min(sizes)))
    means, intervals = {}, {}
    for model, rows in per_user.items():
        intervals[model] = {}
        means[model] = {}
        for metric in ("precision", "recall", "ndcg"):
            values = np.asarray([row[metric] for row in rows])
            sampled = values[draws].mean(axis=1)
            means[model][metric] = sampled
            low, high = np.quantile(sampled, [.025, .975])
            intervals[model][metric + "@10"] = [float(low), float(high)]
    paired = {}
    if "Popularity" in means:
        for model in means:
            low, high = np.quantile(means[model]["ndcg"] - means["Popularity"]["ndcg"],
                                    [.025, .975])
            paired[model] = [float(low), float(high)]
    return intervals, paired


def onboarding_evaluation(movies, past, heldout, alpha, seed_counts=(3, 5, 10),
                          popularity_weight=0, model_parameters=None):
    """Remove every target user's history from training before new-user fold-in."""
    from app.recommender import Recommender
    from src.catalog import latest_ratings
    from src.collaborative import BiasedMF

    histories = {int(uid): group.sort_values("timestamp", kind="stable")
                 for uid, group in latest_ratings(past).groupby("user_id")}
    targets = []
    for uid, group in heldout.groupby("user_id"):
        history = histories.get(int(uid))
        if history is None or len(history) < max(seed_counts):
            continue
        relevant = set(group.loc[group.rating >= 4, "movie_id"]) - set(history.movie_id)
        if relevant:
            targets.append((int(uid), history, relevant))
    target_ids = {uid for uid, _, _ in targets}
    background = past[~past.user_id.isin(target_ids)]
    if not targets or background.empty:
        return {"users": 0, "training_users": 0, "results": []}
    model = BiasedMF(**(model_parameters or {})).fit(latest_ratings(background), movies.movie_id.to_numpy())
    engine = Recommender(movies, background, alpha=alpha, collaborative=model,
                         popularity_weight=popularity_weight)
    records = []
    for count in seed_counts:
        cohort = []
        for _, history, relevant in targets:
            seed = history.tail(count)
            profile = dict(zip(seed.movie_id, seed.rating))
            components = engine.score_components(profile)
            components["genre_available"] = engine.content.scores(profile) is not None
            cohort.append((engine.candidate_indices(profile, media_type="Movie"),
                           components, relevant))
        for model in ALGORITHMS:
            records.append({"seed_ratings": count, "algorithm": model,
                            **evaluate_cohort(engine, cohort, model)})
    return {"users": len(targets), "training_users": int(background.user_id.nunique()),
            "excluded_training_user_ids": sorted(target_ids),
            "protocol": "Matched users with >=10 past ratings. Last N ratings before the "
                        "test boundary are seeds. Entire target-user histories are removed "
                        "from model training. Full supported candidates exclude seeds only; "
                        "future positives exclude all previously seen titles.",
            "results": records}
