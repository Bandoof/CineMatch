"""Validation-only model selection, followed by one frozen offline final evaluation.

Inputs and outputs are explicit directories. No private data, app models, runtime
policy updates or automatic downloads. Install optional research requirements for
MiniLM; otherwise --embedding-dir can be omitted and unavailability is recorded.
"""

import argparse
import importlib.metadata
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.recommender import Recommender
from scripts.download_benchmark import load
from src.catalog import canonical_catalog
from src.collaborative import BiasedMF
from src.content_based import ContentBased
from src.data import ROOT, temporal_split
from src.popularity import Popularity
from src.research_embeddings import CachedEncoder, cache_receipt, load_vectors, save_vectors
from src.research_models import calibrate, content_scores, fold_in_scores
from src.research_onboarding import simulate
from src.research_protocol import (
    background,
    candidates,
    digest_json,
    file_digest,
    paired_summary,
    source_fingerprint,
    summarize,
    targets,
    verify_boundaries,
    write_new_json,
)
from src.semantic import SemanticContent

SOURCE_PATHS = [
    "scripts/research_v12.py",
    "scripts/prepare_research.py",
    "src/research_protocol.py",
    "src/research_models.py",
    "src/research_embeddings.py",
    "src/research_onboarding.py",
    "src/collaborative.py",
    "src/semantic.py",
    "src/discovery.py",
    "src/popularity.py",
    "src/content_based.py",
    "src/catalog.py",
    "src/data.py",
    "src/evaluation.py",
    "app/recommender.py",
]


def peak_rss_mib():
    if sys.platform == "win32":
        return None  # resource is unavailable; never label this as a Windows measurement.
    import resource

    scale = 1024**2 if sys.platform == "darwin" else 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale


def environment():
    packages = {}
    for name in ("numpy", "pandas", "scipy", "scikit-learn", "onnxruntime", "tokenizers"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "processor": platform.processor(),
        "packages": packages,
        "openblas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
        "peak_process_rss_mib": peak_rss_mib(),
    }


def load_inputs(directory, output, phase):
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    if digest_json(config) != manifest["config_sha256"]:
        raise ValueError("Changed configuration.")
    if any(
        file_digest(directory / name) != value for name, value in manifest["input_sha256"].items()
    ):
        raise ValueError("Changed dataset input.")
    historical = ROOT / config["historical_report"]
    if file_digest(historical) != manifest["historical_report_sha256"]:
        raise ValueError("Historical evidence changed.")
    movies, events = load(directory)
    movies, events, _ = canonical_catalog(movies, events)
    train, validation, test = temporal_split(events)
    old = json.loads(historical.read_text(encoding="utf-8"))
    verify_boundaries(
        train,
        validation,
        test,
        manifest["validation_user_ids"],
        manifest["test_user_ids"],
        set(old["validation_user_ids"]) | set(old["test_user_ids"]),
    )
    reserved = set(manifest["validation_user_ids"]) | set(manifest["test_user_ids"])
    past, future = (
        (train, validation)
        if phase == "validation"
        else (pd.concat([train, validation], ignore_index=True), test)
    )
    wanted = manifest["validation_user_ids" if phase == "validation" else "test_user_ids"]
    users = targets(
        past, future[future.user_id.isin(wanted)], set(), len(wanted), config["minimum_history"]
    )
    if [user.user_id for user in users] != wanted:
        raise ValueError("Prepared cohort changed.")
    return manifest, movies, background(past, reserved), users


def profiles_for(users, count):
    return [
        {int(row.movie_id): float(row.rating) for row in user.history.tail(count).itertuples()}
        for user in users
    ]


def train_configurations(config):
    result = [
        {
            "factors": factors,
            "regularization": regularization,
            "bias_regularization": config["bias_regularization"],
            "epochs": config["epochs"],
            "random_state": config["random_state"],
        }
        for factors in config["factors"]
        for regularization in config["regularization"]
    ]
    result.extend(
        {
            "factors": 32,
            "regularization": 10,
            "bias_regularization": bias,
            "epochs": config["epochs"],
            "random_state": config["random_state"],
        }
        for bias in config["additional_bias_regularization"]
    )
    return result


def matrix_bytes(model):
    return sum(
        getattr(model, name).nbytes
        for name in (
            "movie_ids",
            "user_ids",
            "item_factors",
            "user_factors",
            "item_bias",
            "user_bias",
        )
    )


def blend_grid(denominator):
    return [
        (a / denominator, b / denominator, (denominator - a - b) / denominator)
        for a in range(denominator + 1)
        for b in range(denominator + 1 - a)
    ]


def blend_families(weights):
    a, b, p = weights
    result = ["Adaptive-selected"]
    if a > 0 and b == 0 and p > 0:
        result.append("ALS+Quality")
    if a == 0 and b > 0 and p > 0:
        result.append("Content+Quality")
    if a > 0 and b > 0 and p == 0:
        result.append("ALS+Content")
    if a > 0 and b > 0 and p > 0:
        result.append("ALS+Content+Quality")
    return result


def fit_content(movies, ratings, output, embedding_dir):
    started = time.perf_counter()
    lsa = SemanticContent(movies, train_ids=set(ratings.movie_id), dimensions=64, retain_texts=True)
    models = {"tfidf": lsa.tfidf, "lsa64": lsa.features}
    costs = {
        "lexical_fit_seconds": time.perf_counter() - started,
        "metadata": "archive titles + genres; descriptions coverage=0",
        "lsa_dimensions": lsa.dimensions,
        "lsa_matrix_bytes": lsa.features.nbytes,
        "tfidf_matrix_bytes": sum(
            a.nbytes for a in (lsa.tfidf.data, lsa.tfidf.indices, lsa.tfidf.indptr)
        ),
    }
    cache = output / "minilm-vectors.npz"
    if cache.exists():
        started = time.perf_counter()
        models["minilm"] = load_vectors(cache, lsa.ids, lsa.texts)
        costs.update(
            embedding_cache_load_seconds=time.perf_counter() - started,
            embedding_artifact_bytes=cache.stat().st_size,
            embedding_matrix_bytes=models["minilm"].nbytes,
            embedding_artifact_sha256=file_digest(cache),
        )
    elif embedding_dir is not None:
        started = time.perf_counter()
        encoder = CachedEncoder(embedding_dir)
        costs["embedding_encoder_load_seconds"] = time.perf_counter() - started
        started = time.perf_counter()
        models["minilm"] = encoder.encode(lsa.texts)
        costs["embedding_precompute_seconds"] = time.perf_counter() - started
        save_vectors(cache, lsa.ids, models["minilm"], lsa.texts)
        np.testing.assert_allclose(load_vectors(cache, lsa.ids, lsa.texts), models["minilm"])
        costs.update(
            embedding_artifact_bytes=cache.stat().st_size,
            embedding_matrix_bytes=models["minilm"].nbytes,
            embedding_artifact_sha256=file_digest(cache),
            embedding_source=cache_receipt(embedding_dir),
        )
        # A diagnostic, not user-interaction or Ukrainian retrieval-quality evidence.
        sentences = [
            "A detective investigates a mysterious crime.",
            "Детектив розслідує загадковий злочин.",
            "Two people fall in love in a romantic comedy.",
            "Двоє людей закохуються у романтичній комедії.",
            "Astronauts explore distant planets in space.",
            "Астронавти досліджують далекі планети в космосі.",
            "A family watches an animated adventure.",
            "Родина дивиться анімаційну пригоду.",
            "A soldier fights during the war.",
            "Солдат воює під час війни.",
            "A frightening monster haunts a house.",
            "Страшне чудовисько переслідує мешканців будинку.",
        ]
        vectors = encoder.encode(sentences)
        similarity = vectors[1::2] @ vectors[::2].T
        costs["bilingual_sanity"] = {
            "pairs": 6,
            "top1_correct": int((similarity.argmax(axis=1) == np.arange(6)).sum()),
            "cosine_matrix": similarity.tolist(),
            "scope": "Six handcrafted EN/UK pairs; sanity check only, not a retrieval benchmark.",
        }
    else:
        costs["embedding_unavailable"] = (
            "No --embedding-dir or verified cached vectors; lexical models retained."
        )
    return lsa, models, costs


def metric(ids, users, profiles, score, genres, counts, **kwargs):
    return summarize(ids, users, profiles, score, genres, counts, **kwargs)[0]


def validate(directory, output, embedding_dir):
    if (output / "selection.json").exists() or (output / "final-access.json").exists():
        raise FileExistsError("Selection/final evidence exists; use a new reproduction directory.")
    started = time.perf_counter()
    manifest, movies, ratings, users = load_inputs(directory, output, "validation")
    config, ids = manifest["config"], movies.movie_id.to_numpy(dtype=int)
    pop = Popularity().fit(ids, ratings)
    genres = ContentBased(movies).features
    profiles = {n: profiles_for(users, n) for n in config["seed_counts"]}
    pools = {n: [candidates(ids, p) for p in profiles[n]] for n in profiles}
    lsa, representations, content_costs = fit_content(movies, ratings, output, embedding_dir)
    content_costs["warm_profile_scoring"] = {}
    for name, matrix in representations.items():
        samples = []
        for profile in profiles[10][:30]:
            for repeat in range(6):
                tick = time.perf_counter()
                content_scores(matrix, lsa.positions, profile)
                if repeat:
                    samples.append((time.perf_counter() - tick) * 1000)
        content_costs["warm_profile_scoring"][name] = {
            "median_ms": float(np.median(samples)),
            "p95_ms": float(np.quantile(samples, 0.95)),
            "samples": len(samples),
            "scope": "Signed 10-rating vector and full-catalog cosine; no sorting/UI.",
        }
    trials, training_costs, cf_results = [], [], []
    training_hash = digest_json(
        {"manifest": file_digest(output / "manifest.json"), "phase": "validation"}
    )
    cache = output / "models"
    cache.mkdir(exist_ok=True)
    best_value, best_model, best_cf = -np.inf, None, None
    for parameters in train_configurations(config):
        print("Validation fit:", parameters, flush=True)
        tick = time.perf_counter()
        model = BiasedMF(**parameters).fit(ratings, ids)
        fit_seconds = time.perf_counter() - tick
        path = cache / ("validation-" + digest_json(parameters)[:16] + ".npz")
        if path.exists():
            path.unlink()  # Reproducible numeric cache, never published evidence or personal data.
        model.save(path, training_hash)
        tick = time.perf_counter()
        loaded = BiasedMF.load(path, training_hash)
        load_seconds = time.perf_counter() - tick
        np.testing.assert_allclose(
            model.scores(profiles[10][0]), loaded.scores(profiles[10][0]), atol=1e-12
        )
        training_costs.append(
            {
                **parameters,
                "fit_seconds": fit_seconds,
                "load_seconds": load_seconds,
                "matrix_bytes": matrix_bytes(model),
                "artifact_bytes": path.stat().st_size,
                "artifact_sha256": file_digest(path),
                "peak_process_rss_mib": peak_rss_mib(),
            }
        )
        for strength in config["fold_in_regularization"] + ["training"]:
            raw = {
                n: [
                    fold_in_scores(model, profile, None if strength == "training" else strength)
                    for profile in profiles[n]
                ]
                for n in profiles
            }
            for mode in config["calibration"]:
                results = []
                for n in profiles:
                    scores = [
                        calibrate(score, pool, "cf", mode) for score, pool in zip(raw[n], pools[n])
                    ]
                    summary = metric(ids, users, profiles[n], scores, genres, pop.counts)
                    results.append(summary["ndcg@10"])
                    trials.append(
                        {
                            "family": "collaborative",
                            "parameters": parameters,
                            "fold_in": strength,
                            "calibration": mode,
                            "seed_ratings": n,
                            **summary,
                        }
                    )
                value = float(np.mean(results))
                record = {
                    "parameters": parameters,
                    "fold_in": strength,
                    "calibration": mode,
                    "mean_seed_ndcg@10": value,
                }
                cf_results.append(record)
                if value > best_value:
                    best_value, best_model, best_cf = value, model, record
    print("Selected collaborative:", best_cf, flush=True)
    semantic_results, best_sem, best_value = [], None, -np.inf
    for name, matrix in representations.items():
        for preference in config["preference"]:
            results = []
            for n in profiles:
                raw = [
                    content_scores(matrix, lsa.positions, profile, preference)
                    for profile in profiles[n]
                ]
                scores = [
                    calibrate(pop.scores, pool, "quality")
                    if score is None
                    else calibrate(score, pool, "content")
                    for score, pool in zip(raw, pools[n])
                ]
                summary = metric(ids, users, profiles[n], scores, genres, pop.counts)
                results.append(summary["ndcg@10"])
                trials.append(
                    {
                        "family": "content",
                        "representation": name,
                        "preference": preference,
                        "seed_ratings": n,
                        "undefined_profiles": sum(x is None for x in raw),
                        **summary,
                    }
                )
            record = {
                "representation": name,
                "preference": preference,
                "mean_seed_ndcg@10": float(np.mean(results)),
            }
            semantic_results.append(record)
            if record["mean_seed_ndcg@10"] > best_value:
                best_value, best_sem = record["mean_seed_ndcg@10"], record
    print("Selected content:", best_sem, flush=True)
    blends = {}
    for n in profiles:
        cf = [
            fold_in_scores(
                best_model,
                profile,
                None if best_cf["fold_in"] == "training" else best_cf["fold_in"],
            )
            for profile in profiles[n]
        ]
        sem = [
            content_scores(
                representations[best_sem["representation"]],
                lsa.positions,
                profile,
                best_sem["preference"],
            )
            for profile in profiles[n]
        ]
        best = {}
        for mode in config["calibration"]:
            components = np.asarray(
                [
                    [
                        calibrate(c, pool, "cf", mode),
                        calibrate(pop.scores, pool, "quality", mode)
                        if s is None
                        else calibrate(s, pool, "content", mode),
                        calibrate(pop.scores, pool, "quality", mode),
                    ]
                    for c, s, pool in zip(cf, sem, pools[n])
                ]
            )
            for weights in blend_grid(config["blend_denominator"]):
                scores = np.sum(components * np.asarray(weights)[None, :, None], axis=1)
                summary = metric(ids, users, profiles[n], scores, genres, pop.counts)
                record = {"weights": list(weights), "calibration": mode, **summary}
                trials.append({"family": "blend", "seed_ratings": n, **record})
                for family in blend_families(weights):
                    if family not in best or summary["ndcg@10"] > best[family]["ndcg@10"]:
                        best[family] = record
        blends[str(n)] = best
        print("Validation blend:", n, best["Adaptive-selected"], flush=True)
    selection = {
        "protocol_version": 12,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": file_digest(output / "manifest.json"),
        "source_sha256": source_fingerprint(ROOT, SOURCE_PATHS),
        "source_paths": SOURCE_PATHS,
        "config_sha256": manifest["config_sha256"],
        "selected_cf": best_cf,
        "selected_content": best_sem,
        "blends": blends,
        "available_content_models": list(representations),
        "embedding_artifact_sha256": content_costs.get("embedding_artifact_sha256"),
        "validation_users": len(users),
        "background_events": len(ratings),
        "collaborative_candidates": cf_results,
        "semantic_candidates": semantic_results,
        "training_costs": training_costs,
        "content_costs": content_costs,
        "environment": environment(),
        "seconds": time.perf_counter() - started,
        "integration": "Frozen research configurations; production policy unchanged.",
    }
    write_new_json(output / "validation.json", {"trials": trials, "selection": selection})
    write_new_json(output / "selection.json", selection)
    print("Frozen selection:", digest_json(selection), flush=True)
    return selection


def verify_selection(output):
    selection = json.loads((output / "selection.json").read_text(encoding="utf-8"))
    if file_digest(output / "manifest.json") != selection["manifest_sha256"]:
        raise ValueError("Prepared manifest changed after validation.")
    if source_fingerprint(ROOT, selection["source_paths"]) != selection["source_sha256"]:
        raise ValueError("Research source changed after selection; no final access permitted.")
    if selection["embedding_artifact_sha256"] is not None:
        if file_digest(output / "minilm-vectors.npz") != selection["embedding_artifact_sha256"]:
            raise ValueError("Embedding artifact changed after selection.")
    return selection


def timed_score(
    model, representation, positions, users, selected_cf, selected_content, blend, ids, quality
):
    samples = []
    for user in users[:30]:
        profile = profiles_for([user], 10)[0]
        pool = candidates(ids, profile)
        for repeat in range(6):
            tick = time.perf_counter()
            cf = fold_in_scores(
                model,
                profile,
                None if selected_cf["fold_in"] == "training" else selected_cf["fold_in"],
            )
            sem = content_scores(representation, positions, profile, selected_content["preference"])
            mode = blend["calibration"]
            q = calibrate(quality, pool, "quality", mode)
            c = calibrate(cf, pool, "cf", mode)
            s = q if sem is None else calibrate(sem, pool, "content", mode)
            a, b, p = blend["weights"]
            score = a * c + b * s + p * q
            np.lexsort((ids[pool], -score[pool]))[:10]
            if repeat:
                samples.append((time.perf_counter() - tick) * 1000)
    return {
        "median_ms": float(np.median(samples)),
        "p95_ms": float(np.quantile(samples, 0.95)),
        "samples": len(samples),
        "scope": "Frozen Adaptive-selected scoring, candidate construction excluded; "
        "includes CF/content/quality calibration, weighted blend and Top-10 sort; excludes UI/network.",
    }


def final(directory, output):
    selection = verify_selection(output)
    # Reserve before reading/scoring test labels. A crash still records access.
    write_new_json(
        output / "final-access.json",
        {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "selection_sha256": digest_json(selection),
            "warning": "Final labels accessed once. Subsequent runs are replications, never a new holdout.",
        },
    )
    started = time.perf_counter()
    manifest, movies, ratings, users = load_inputs(directory, output, "test")
    config, ids = manifest["config"], movies.movie_id.to_numpy(dtype=int)
    pop, genre_model = Popularity().fit(ids, ratings), ContentBased(movies)
    lsa, representations, content_costs = fit_content(movies, ratings, output, None)
    if set(representations) != set(selection["available_content_models"]):
        raise ValueError("Representation availability changed after selection.")
    tick = time.perf_counter()
    parameters = selection["selected_cf"]["parameters"]
    model = BiasedMF(**parameters).fit(ratings, ids)
    fit_seconds = time.perf_counter() - tick
    baseline_parameters = {
        "factors": 32,
        "regularization": 10,
        "bias_regularization": 5,
        "epochs": config["epochs"],
        "random_state": config["random_state"],
    }
    baseline = (
        model
        if parameters == baseline_parameters
        else BiasedMF(**baseline_parameters).fit(ratings, ids)
    )
    artifact = output / "models/final-selected.npz"
    model.save(
        artifact, digest_json({"manifest": file_digest(output / "manifest.json"), "phase": "test"})
    )
    engine = Recommender(movies, ratings, collaborative=model)
    engine.attach_content(lsa)
    records, intervals, diagnostics, raw_rows, recommendations = [], {}, {}, [], {}
    for n in config["seed_counts"]:
        profiles = profiles_for(users, n)
        pools = [candidates(ids, p) for p in profiles]
        p = [calibrate(pop.scores, pool, "quality") for pool in pools]
        cf = [
            fold_in_scores(
                model,
                profile,
                None
                if selection["selected_cf"]["fold_in"] == "training"
                else selection["selected_cf"]["fold_in"],
            )
            for profile in profiles
        ]
        sem = [
            content_scores(
                representations[selection["selected_content"]["representation"]],
                lsa.positions,
                profile,
                selection["selected_content"]["preference"],
            )
            for profile in profiles
        ]
        scores = {
            "Popularity": p,
            "ALS-v3-fixed": [
                calibrate(baseline.scores(profile), pool, "cf")
                for profile, pool in zip(profiles, pools)
            ],
            "ALS-selected": [
                calibrate(score, pool, "cf", selection["selected_cf"]["calibration"])
                for score, pool in zip(cf, pools)
            ],
        }
        for name, matrix in representations.items():
            raw = [content_scores(matrix, lsa.positions, profile) for profile in profiles]
            scores[name + "-signed"] = [
                quality if s is None else calibrate(s, pool, "content")
                for s, pool, quality in zip(raw, pools, p)
            ]
        scores["Content-selected"] = [
            quality if s is None else calibrate(s, pool, "content")
            for s, pool, quality in zip(sem, pools, p)
        ]
        for family, blend in selection["blends"][str(n)].items():
            mode, weights = blend["calibration"], blend["weights"]
            scores[family] = [
                weights[0] * calibrate(c, pool, "cf", mode)
                + weights[1]
                * (
                    calibrate(pop.scores, pool, "quality", mode)
                    if s is None
                    else calibrate(s, pool, "content", mode)
                )
                + weights[2] * calibrate(pop.scores, pool, "quality", mode)
                for c, s, pool in zip(cf, sem, pools)
            ]
        per_user = {}
        for name, values in scores.items():
            summary, rows, recs = summarize(
                ids, users, profiles, values, genre_model.features, pop.counts
            )
            records.append({"seed_ratings": n, "algorithm": name, **summary})
            per_user[name] = rows
            recommendations[(n, name)] = recs
            raw_rows.extend(
                {"seed_ratings": n, "algorithm": name, "user_id": user.user_id, **row}
                for user, row in zip(users, rows)
            )
        intervals[str(n)] = paired_summary(
            per_user, config["bootstrap_resamples"], config["bootstrap_seed"]
        )
        for name in ("Popularity", "ALS-v3-fixed", "Adaptive-selected"):
            summary, _, _ = summarize(
                ids,
                users,
                profiles,
                scores[name],
                genre_model.features,
                pop.counts,
                full_history=True,
            )
            diagnostics.setdefault("full_history_filter", []).append(
                {"seed_ratings": n, "algorithm": name, **summary}
            )
        clipped = np.asarray([baseline.scores(profile) for profile in profiles])
        diagnostics.setdefault("score_distribution", []).append(
            {
                "seed_ratings": n,
                "baseline_cf_below_1_fraction": float((clipped < 1).mean()),
                "baseline_cf_above_5_fraction": float((clipped > 5).mean()),
                "mean_profile_rating": float(
                    np.mean([np.mean(list(profile.values())) for profile in profiles])
                ),
                "mean_high_rating_fraction": float(
                    np.mean(
                        [np.mean(np.asarray(list(profile.values())) >= 4) for profile in profiles]
                    )
                ),
                "selected_content_undefined_profiles": sum(s is None for s in sem),
            }
        )
        print(
            "Final primary:",
            n,
            next(
                row
                for row in records
                if row["seed_ratings"] == n and row["algorithm"] == "Adaptive-selected"
            ),
            flush=True,
        )
    onboarding, onboarding_intervals = [], {}
    for strategy in config["onboarding"]:
        print("Final onboarding:", strategy, flush=True)
        supplied, costs = [], []
        for user in users:
            snapshots, prompt_cost = simulate(engine, user, strategy, tuple(config["seed_counts"]))
            supplied.append(snapshots)
            costs.append(prompt_cost)
        for n in config["seed_counts"]:
            profiles = [row[n] for row in supplied]
            blend = selection["blends"][str(n)]["Adaptive-selected"]
            values, popular = [], []
            for profile in profiles:
                pool = candidates(ids, profile)
                cf = fold_in_scores(
                    model,
                    profile,
                    None
                    if selection["selected_cf"]["fold_in"] == "training"
                    else selection["selected_cf"]["fold_in"],
                )
                sem = content_scores(
                    representations[selection["selected_content"]["representation"]],
                    lsa.positions,
                    profile,
                    selection["selected_content"]["preference"],
                )
                q = calibrate(pop.scores, pool, "quality", blend["calibration"])
                s = q if sem is None else calibrate(sem, pool, "content", blend["calibration"])
                c = calibrate(cf, pool, "cf", blend["calibration"])
                a, b, p = blend["weights"]
                values.append(a * c + b * s + p * q)
                popular.append(calibrate(pop.scores, pool, "quality"))
            summary, rows, _ = summarize(
                ids, users, profiles, values, genre_model.features, pop.counts
            )
            base, base_rows, _ = summarize(
                ids, users, profiles, popular, genre_model.features, pop.counts
            )
            onboarding.append(
                {
                    "seed_ratings": n,
                    "strategy": strategy,
                    "model": "frozen Adaptive-selected",
                    **summary,
                    "median_prompts": float(np.median([row[n] for row in costs])),
                    "p90_prompts": float(np.quantile([row[n] for row in costs], 0.9)),
                    "mean_observed_rating_availability": float(
                        np.mean([n / row[n] for row in costs])
                    ),
                    "matched_popularity_ndcg@10": base["ndcg@10"],
                }
            )
            onboarding_intervals[f"{strategy}:{n}"] = paired_summary(
                {"Popularity": base_rows, "Strategy": rows},
                config["bootstrap_resamples"],
                config["bootstrap_seed"],
            )
    selected_rep = representations[selection["selected_content"]["representation"]]
    timings = timed_score(
        model,
        selected_rep,
        lsa.positions,
        users,
        selection["selected_cf"],
        selection["selected_content"],
        selection["blends"]["10"]["Adaptive-selected"],
        ids,
        pop.scores,
    )
    # Error strata use pre-boundary activity and background counts, never tuning outcomes.
    user_groups = {
        "history_20_99": [i for i, user in enumerate(users) if len(user.history) < 100],
        "history_100_plus": [i for i, user in enumerate(users) if len(user.history) >= 100],
    }
    for group, indices in user_groups.items():
        diagnostics.setdefault("activity_strata", []).append(
            {
                "group": group,
                "users": len(indices),
                "ndcg@10": {
                    name: float(
                        np.mean(
                            [
                                row["ndcg"]
                                for row in raw_rows
                                if row["seed_ratings"] == 3
                                and row["algorithm"] == name
                                and row["user_id"] in {users[i].user_id for i in indices}
                            ]
                        )
                    )
                    if indices
                    else None
                    for name in ("Popularity", "ALS-v3-fixed", "Adaptive-selected")
                },
            }
        )
    result = {
        "protocol_version": 12,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest,
        "selection_sha256": digest_json(selection),
        "selection": selection,
        "test_users": len(users),
        "background_events": len(ratings),
        "results": records,
        "intervals": intervals,
        "diagnostics": diagnostics,
        "onboarding": onboarding,
        "onboarding_intervals": onboarding_intervals,
        "content_costs": content_costs,
        "selected_als_fit_seconds": fit_seconds,
        "selected_als_matrix_bytes": matrix_bytes(model),
        "selected_als_artifact_bytes": artifact.stat().st_size,
        "selected_als_artifact_sha256": file_digest(artifact),
        "warm_scoring": timings,
        "environment": environment(),
        "seconds": time.perf_counter() - started,
        "scope": "Full-catalog matched new-user MovieLens experiment, archive titles/genres only. "
        "Retrospective pretrained weights, no series, dismissal, or live-quality evidence. "
        "Onboarding is an oracle of past-rated familiarity, not a live active-learning gain. "
        "Production ranking policy and private database unchanged.",
    }
    write_new_json(output / "final.json", result)
    pd.DataFrame(records).to_csv(output / "final.csv", index=False)
    pd.DataFrame(raw_rows).to_csv(output / "per-user-metrics.csv", index=False)
    print("Final saved:", output / "final.json", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("validation", "final"))
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--embedding-dir", type=Path)
    args = parser.parse_args()
    if args.phase == "validation":
        validate(args.data_dir, args.output, args.embedding_dir)
    else:
        if args.embedding_dir is not None:
            parser.error("Final evaluation only uses frozen precomputed vectors.")
        final(args.data_dir, args.output)


if __name__ == "__main__":
    main()
