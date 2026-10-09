"""Tune the expanded development snapshot on validation; compare on one test cohort."""

import json
from datetime import datetime, timezone

import pandas as pd

from app.recommender import ALGORITHMS, Recommender
from src.catalog import latest_ratings
from src.collaborative import BiasedMF
from src.data import ROOT, fingerprint, load_app_movies, temporal_split
from src.evaluation import (bootstrap_intervals, evaluate_cohort, onboarding_evaluation,
                            prepare_cohort)
from src.reporting import benchmark_markdown


def improve():
    movies, events = load_app_movies()
    train, validation, test = temporal_split(events)
    digest = fingerprint(movies, events)
    print(f"Expanded: {len(movies)} films, {len(events)} events; split {len(train)}/{len(validation)}/{len(test)}", flush=True)
    candidates = [(24, 5), (16, 10), (32, 10), (32, 2)]
    trials = []
    for factors, regularization in candidates:
        print(f"Validation: factors={factors}, regularization={regularization}", flush=True)
        mf = BiasedMF(factors=factors, regularization=regularization).fit(latest_ratings(train), movies.movie_id.to_numpy())
        engine = Recommender(movies, train, collaborative=mf)
        cohort, validation_details = prepare_cohort(engine, validation)
        for alpha in (.25, .5, .75, 1.0):
            for beta in (0, .2, .4, .6):
                trials.append({"factors": factors, "regularization": regularization,
                    "alpha": alpha, "popularity_weight": beta,
                    **evaluate_cohort(engine, cohort, "Hybrid", alpha=alpha, popularity_weight=beta)})
        print(f"Current best validation NDCG: {max(row['ndcg@10'] for row in trials):.4f}", flush=True)
    best = max(trials, key=lambda row: row["ndcg@10"])
    past = pd.concat([train, validation], ignore_index=True)
    print(f"Selected on validation: {best}; refitting train+validation", flush=True)
    mf = BiasedMF(factors=best["factors"], regularization=best["regularization"]).fit(
        latest_ratings(past), movies.movie_id.to_numpy())
    final = Recommender(movies, past, collaborative=mf, alpha=best["alpha"],
                        popularity_weight=best["popularity_weight"])
    cohort, details = prepare_cohort(final, test)
    metrics, per_user = {}, {}
    for model in ALGORITHMS:
        metrics[model], per_user[model] = evaluate_cohort(final, cohort, model, return_users=True)
    # Old default architecture on precisely the same expanded data and labels.
    baseline = Recommender(movies, past, alpha=1.0)
    baseline_cohort, baseline_details = prepare_cohort(baseline, test)
    assert details == baseline_details
    old_metrics, old_users = evaluate_cohort(baseline, baseline_cohort, "Hybrid", return_users=True)
    confidence, paired = bootstrap_intervals(per_user)
    _, paired_comparison = bootstrap_intervals({"Popularity": old_users, "Improved": per_user["Hybrid"]})
    print(f"Same-cohort test NDCG: previous {old_metrics['ndcg@10']:.4f}, updated {metrics['Hybrid']['ndcg@10']:.4f}", flush=True)
    # Existing onboarding evaluates film models without app-only negative feedback.
    onboarding = onboarding_evaluation(movies, past, test, best["alpha"],
        popularity_weight=best["popularity_weight"],
        model_parameters={"factors": best["factors"], "regularization": best["regularization"]})
    report = {"protocol_version": 2, "dataset": "MovieLens 100K + latest-small pinned development snapshot",
        "canonical_films": len(movies), "source_rating_events": len(events), "fingerprint": digest,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "split": {"train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test),
                  "train_cutoff": int(train.timestamp.max()), "validation_cutoff": int(validation.timestamp.max()),
                  "test_start": int(test.timestamp.min())},
        "selected_alpha": best["alpha"], "selected_popularity_weight": best["popularity_weight"],
        "model": {"factors": best["factors"], "regularization": best["regularization"], "epochs": 15, "seed": 42},
        "validation_trials": trials, "validation_cohort": validation_details, "test_cohort": details,
        "metrics": metrics, "confidence_95": confidence, "paired_ndcg_vs_popularity_95": paired,
        "bootstrap_resamples": 1000, "onboarding": onboarding,
        "diversity_analysis": [{"weight": weight, **evaluate_cohort(final, cohort, "Hybrid", diversity=weight)}
                               for weight in (0, .25, .5, .75)],
        "previous_model_same_cohort": old_metrics, "paired_improved_minus_previous_ndcg_95": paired_comparison["Improved"],
        "snapshot": json.loads((ROOT / "data/ml-latest-small/source.json").read_text(encoding="utf-8")),
        "protocol": "Global chronological 80/10/10 split with timestamp ties. Validation-only ALS/Hybrid tuning. "
                    "Full past-supported film catalog, all known titles excluded, unseen future rating >=4 relevant. "
                    "User namespaces kept separate. App artifacts never used by evaluation. Series and not-interested feedback "
                    "are not evaluated. Development snapshot; not comparable to the original 100K benchmark."}
    destination = ROOT / "reports"
    destination.mkdir(exist_ok=True)
    (destination / "expanded_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    pd.DataFrame.from_dict(metrics, orient="index").rename_axis("algorithm").to_csv(destination / "expanded_metrics.csv")
    (destination / "expanded_benchmark.md").write_text(benchmark_markdown(report), encoding="utf-8")
    with (destination / "expanded_benchmark.md").open("a", encoding="utf-8") as output:
        output.write(f"\n## Expanded configuration and previous-model comparison\n\n"
            f"Dataset: {report['dataset']}. Source checksum: `{report['snapshot']['archive_sha256']}`.\n\n"
            f"ALS: {best['factors']} factors, regularization {best['regularization']}; "
            f"Hybrid community-quality weight {best['popularity_weight']}.\n\n"
            f"Same {len(cohort)}-user cohort: previous NDCG@10 {old_metrics['ndcg@10']:.4f}, "
            f"updated {metrics['Hybrid']['ndcg@10']:.4f}. "
            f"Paired 95% interval: {paired_comparison['Improved']}. "
            "No reliable overall accuracy improvement is established.\n")
    print("Training full-data app artifact with validation-selected parameters", flush=True)
    deployed = BiasedMF(factors=best["factors"], regularization=best["regularization"]).fit(
        latest_ratings(events), movies.movie_id.to_numpy())
    deployed.save(ROOT / "models/expanded.npz", digest)
    print("Expanded app model ready.", flush=True)


if __name__ == "__main__":
    improve()
