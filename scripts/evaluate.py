"""Tune only on validation, then refit past observations and evaluate test once."""

import json
from datetime import datetime, timezone

import pandas as pd

from app.recommender import Recommender
from src.data import ROOT, fingerprint, load_movielens, temporal_split
from app.recommender import ALGORITHMS
from src.evaluation import (bootstrap_intervals, evaluate_cohort,
                            onboarding_evaluation, prepare_cohort)
from src.reporting import benchmark_markdown


def evaluate():
    movies, ratings = load_movielens()
    train, validation, test = temporal_split(ratings)
    print(f"Global temporal split: {len(train)}/{len(validation)}/{len(test)}", flush=True)
    engine = Recommender(movies, train)
    cohort, validation_details = prepare_cohort(engine, validation)
    trials = [{"alpha": alpha, **evaluate_cohort(engine, cohort, "Hybrid", alpha=alpha)}
              for alpha in (0.0, 0.25, 0.5, 0.75, 1.0)]
    selected = max(trials, key=lambda row: row["ndcg@10"])["alpha"]
    print(f"Validation selected alpha={selected}; refitting train+validation", flush=True)
    past = pd.concat([train, validation], ignore_index=True)
    final = Recommender(movies, past, alpha=selected)
    test_cohort, details = prepare_cohort(final, test)
    metrics, per_user = {}, {}
    for model in ALGORITHMS:
        metrics[model], per_user[model] = evaluate_cohort(final, test_cohort, model,
                                                        return_users=True)
    confidence, paired = bootstrap_intervals(per_user)
    variety = [{"weight": weight, **evaluate_cohort(final, test_cohort, "Hybrid", diversity=weight)}
               for weight in (0, .25, .5, .75)]
    print("Evaluating new-user onboarding with 3, 5 and 10 ratings", flush=True)
    onboarding = onboarding_evaluation(movies, past, test, selected)
    report = {
        "protocol_version": 2, "dataset": "MovieLens 100K",
        "canonical_films": len(movies), "source_rating_events": len(ratings),
        "fingerprint": fingerprint(movies, ratings),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "split": {"train_rows": len(train), "validation_rows": len(validation),
                  "test_rows": len(test), "train_cutoff": int(train.timestamp.max()),
                  "validation_cutoff": int(validation.timestamp.max()),
                  "test_start": int(test.timestamp.min())},
        "model": {"factors": 24, "epochs": 15, "regularization": 5, "seed": 42},
        "selected_alpha": selected, "validation_trials": trials,
        "validation_cohort": validation_details, "test_cohort": details,
        "metrics": metrics, "confidence_95": confidence,
        "paired_ndcg_vs_popularity_95": paired, "bootstrap_resamples": 1000,
        "onboarding": onboarding, "diversity_analysis": variety,
        "protocol": "Global temporal split; full training-supported catalog; all seen items "
                    "excluded; rating >=4 relevant; macro mean over warm users with positives; "
                    "unavailable positives remain in recall/NDCG denominators; new user fold-in.",
    }
    directory = ROOT / "reports"
    directory.mkdir(exist_ok=True)
    (directory / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    table = pd.DataFrame.from_dict(metrics, orient="index").rename_axis("algorithm")
    table.to_csv(directory / "metrics.csv")
    (directory / "benchmark.md").write_text(benchmark_markdown(report), encoding="utf-8")
    print(table.round(4).to_string())


if __name__ == "__main__":
    evaluate()
