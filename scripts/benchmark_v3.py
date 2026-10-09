"""Independent 1M new-user benchmark. Mixing selected on validation, never test.

Current source extracts are retrospective metadata, not historical snapshots.
Vocabulary/LSA fit only on background-supported titles; targets' histories removed.
"""
import hashlib
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.recommender import Recommender
from scripts.download_benchmark import load
from src.catalog import canonical_catalog, latest_ratings
from src.collaborative import BiasedMF
from src.data import ROOT, temporal_split
from src.evaluation import bootstrap_intervals, ranking_metrics
from src.semantic import SemanticContent


def targets(past, heldout, maximum):
    histories = {int(uid): g.sort_values("timestamp", kind="stable") for uid, g in latest_ratings(past).groupby("user_id")}
    users = []
    for uid, group in heldout.groupby("user_id"):
        history = histories.get(int(uid))
        if history is None or len(history) < 10:
            continue
        relevant = set(group.loc[group.rating >= 4, "movie_id"]) - set(history.movie_id)
        if relevant:
            users.append((int(uid), history, relevant))
    # Predefined, label-independent user hash; no cherry-picking model outcomes.
    users.sort(key=lambda row: hashlib.sha256(f"CineMatch-v3:{row[0]}".encode()).hexdigest())
    return users[:maximum]


def build(movies, past, users):
    ids = {uid for uid, _, _ in users}
    background = latest_ratings(past[~past.user_id.isin(ids)])
    model = BiasedMF(factors=32, regularization=10).fit(background, movies.movie_id.to_numpy())
    engine = Recommender(movies, background, collaborative=model)
    semantic = SemanticContent.load(engine.movies, ROOT / "data/metadata/content.json",
                                    train_ids=set(background.movie_id))
    engine.attach_content(semantic)
    return engine


def cohort(engine, users, count):
    rows = []
    for _, history, relevant in users:
        profile = dict(zip(history.tail(count).movie_id, history.tail(count).rating))
        # Content retrieval admits unsupported items; no future vote statistics.
        candidates = engine.candidate_indices(profile, media_type="Movie", min_ratings=0)
        p = (np.clip(engine.popularity.scores, 1, 5)-1)/4
        cf = (np.clip(engine.collaborative.scores(profile), 1, 5)-1)/4
        s = engine.semantic.scores(profile)
        s = p.copy() if s is None else (np.clip(s, -1, 1)+1)/2
        genre = engine.content.scores(profile)
        genre = p.copy() if genre is None else (np.clip(genre, -1, 1)+1)/2
        rows.append((candidates, (cf, s, p, genre), relevant))
    return rows


def evaluate(engine, rows, weights=None, component=None):
    per_user, unique, distances, novelties = [], set(), [], []
    counts = engine.popularity.counts
    probabilities = (counts+1)/(counts.sum()+len(counts))
    for candidates, components, relevant in rows:
        score = components[component] if component is not None else sum(w*c for w, c in zip(weights, components))
        order = candidates[np.lexsort((engine.movie_ids[candidates], -score[candidates]))[:10]]
        per_user.append(ranking_metrics(engine.movie_ids[order], relevant))
        unique.update(engine.movie_ids[order])
        distances.append(engine.content.diversity(order))
        novelties.append(float((-np.log2(probabilities[order])).mean()))
    summary = {name+"@10": float(np.mean([row[name] for row in per_user])) for name in ("precision", "recall", "ndcg")}
    summary.update(coverage=len(unique)/len(engine.movie_ids), diversity=float(np.mean(distances)),
                   novelty_bits=float(np.mean(novelties)))
    return summary, per_user


def run():
    started = time.perf_counter()
    movies, events = load()
    movies, events, _ = canonical_catalog(movies, events)
    train, validation, test = temporal_split(events)
    print(f"1M: {len(events)} events / {events.user_id.nunique()} users / {len(movies)} films", flush=True)
    val_users = targets(train, validation, 300)
    print(f"Validation new-user simulation: {len(val_users)} users", flush=True)
    engine = build(movies, train, val_users)
    grids = [(c/4, s/4, (4-c-s)/4) for c in range(5) for s in range(5-c)]
    policies, trials = {}, []
    for count in (3, 5, 10):
        rows = cohort(engine, val_users, count)
        results = [{"seed_ratings": count, "weights": list(w), **evaluate(engine, rows, weights=w)[0]} for w in grids]
        best = max(results, key=lambda row: row["ndcg@10"])
        policies[str(count)] = best["weights"]
        trials.extend(results)
        print("Validation selected:", count, best, flush=True)
    past = pd.concat([train, validation], ignore_index=True)
    test_users = targets(past, test, 600)
    print(f"Independent test: {len(test_users)} users; refitting without their histories", flush=True)
    final = build(movies, past, test_users)
    records, intervals, paired = [], {}, {}
    for count in (3, 5, 10):
        rows = cohort(final, test_users, count)
        per_user = {}
        for name, component in (("Popularity", 2), ("Collaborative", 0), ("Semantic", 1), ("Genres", 3)):
            metrics, values = evaluate(final, rows, component=component)
            records.append({"seed_ratings": count, "algorithm": name, **metrics})
            per_user[name] = values
        metrics, values = evaluate(final, rows, weights=policies[str(count)])
        records.append({"seed_ratings": count, "algorithm": "Adaptive", **metrics})
        per_user["Adaptive"] = values
        intervals[str(count)], paired[str(count)] = bootstrap_intervals(per_user)
        print("Test:", count, metrics, flush=True)
    content_path = ROOT / "data/metadata/content.json"
    document = {"protocol_version": 3, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "MovieLens 1M", "source": json.loads((ROOT / "data/ml-1m/source.json").read_text()),
        "events": len(events), "catalog": len(movies), "source_users": int(events.user_id.nunique()),
        "split": {"train": len(train), "validation": len(validation), "test": len(test),
                  "train_cutoff": int(train.timestamp.max()), "validation_cutoff": int(validation.timestamp.max())},
        "validation_users": len(val_users), "test_users": len(test_users),
        "validation_user_ids": [uid for uid, _, _ in val_users], "test_user_ids": [uid for uid, _, _ in test_users],
        "validation_test_user_overlap": len({u for u, _, _ in val_users} & {u for u, _, _ in test_users}),
        "background_events": {"validation": len(engine.ratings), "test": len(final.ratings)},
        "model": {"factors": 32, "epochs": 15, "regularization": 10, "random_state": 42},
        "content_model": {"method": "TF-IDF + TruncatedSVD (LSA)", "max_features": 24000,
                          "dimensions": final.semantic.dimensions, "random_state": 42},
        "selected_policy": policies, "validation_trials": trials, "results": records,
        "confidence_95": intervals, "paired_ndcg_vs_popularity_95": paired,
        "metadata_sha256": hashlib.sha256(content_path.read_bytes()).hexdigest() if content_path.exists() else None,
        "text_coverage": int(final.semantic.covered.sum()), "latent_dimensions": final.semantic.dimensions,
        "seconds": time.perf_counter()-started,
        "scope": "Simulated new users; entire target histories removed from background training. Last N pre-boundary ratings are seeds. Full catalog candidates exclude seeds; positives exclude all earlier history. 300 validation / max 600 test users selected by fixed ID hash. Current Wikipedia/TVmaze metadata is retrospective; not an as-of historical metadata guarantee. Series/negative-feedback/live satisfaction not measured. Mixing policy transfers to the separate expanded app; deployment quality must be checked independently."}
    destination = ROOT / "reports/ml_v3.json"
    destination.write_text(json.dumps(document, indent=2), encoding="utf-8")
    pd.DataFrame(records).to_csv(ROOT / "reports/ml_v3.csv", index=False)
    print("Saved:", destination, flush=True)


if __name__ == "__main__":
    run()
