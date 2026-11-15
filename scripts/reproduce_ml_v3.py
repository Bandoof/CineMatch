"""Reproduce the MovieLens 1M protocol-3 experiment with one command.

    python -m scripts.reproduce_ml_v3

Downloads what is missing (MovieLens 1M, then the metadata/content chain), re-runs
scripts.benchmark_v3 unchanged, adds user-bootstrap intervals for every metric and
compares each number with the recorded reports/ml_v3.json. Output goes to
reports/ml_v3_repro.json and reports/ml_v3_repro.md. The recorded reports/ml_v3.*
files are frozen evidence (hash-checked) and are never modified here.

The content snapshot (data/metadata/content.json) is rebuilt from live Wikipedia,
Wikidata and TVmaze, so it cannot match the 2026-10-09 bytes. Semantic results,
and Adaptive whenever its policy gives LSA a weight, depend on that snapshot.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.data import ROOT
from src.evaluation import bootstrap_all_metrics

HISTORICAL = ROOT / "reports" / "ml_v3.json"
CONTENT = ROOT / "data" / "metadata" / "content.json"
TOLERANCE = 1e-6
METRICS = ("precision@10", "recall@10", "ndcg@10", "coverage", "diversity", "novelty_bits")
# Each step is skipped when its output already exists (resumable, explicit downloads).
CONTENT_CHAIN = (
    ("download_data", "data/ml-100k/u.data"),
    ("download_movies", "data/ml-latest-small/ratings.csv"),
    ("download_series", "data/tvmaze/series.json"),
    ("download_metadata", "data/metadata/catalog.json"),
    ("download_content", "data/metadata/content.json"),
)


def digest(values):
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def run_step(module):
    print(f"$ python -m scripts.{module}", flush=True)
    subprocess.run([sys.executable, "-m", f"scripts.{module}"], cwd=ROOT, check=True)


def ensure_inputs(historical, fetch_content):
    receipt = ROOT / "data" / "ml-1m" / "source.json"
    if not receipt.exists():
        run_step("download_benchmark")
    actual = json.loads(receipt.read_text(encoding="utf-8"))["sha256"]
    if actual != historical["source"]["sha256"]:
        raise SystemExit(f"MovieLens 1M archive differs from the recorded one: {actual}")
    missing = [(m, p) for m, p in CONTENT_CHAIN if not (ROOT / p).exists()]
    if missing and not fetch_content:
        raise SystemExit("Content snapshot missing; rerun without --no-fetch-content.")
    if missing:
        print(
            "WARNING: rebuilding the content snapshot queries Wikipedia, Wikidata and "
            "TVmaze for thousands of titles; this can take tens of minutes.",
            flush=True,
        )
        for module, _ in missing:
            run_step(module)


def content_dependent(algorithm, seeds, historical, reproduced):
    if algorithm == "Semantic":
        return True
    if algorithm != "Adaptive":
        return False
    policies = (historical["selected_policy"][seeds], reproduced["selected_policy"][seeds])
    return any(policy[1] > 0 for policy in policies)


def compare(historical, reproduced):
    rows = []
    recorded = {(r["seed_ratings"], r["algorithm"]): r for r in historical["results"]}
    for row in reproduced["results"]:
        key = (row["seed_ratings"], row["algorithm"])
        old = recorded[key]
        diffs = {m: row[m] - old[m] for m in METRICS}
        worst = max(abs(d) for d in diffs.values())
        dependent = content_dependent(key[1], str(key[0]), historical, reproduced)
        status = (
            "match"
            if worst <= TOLERANCE
            else ("differs (content snapshot)" if dependent else "differs")
        )
        rows.append(
            {
                "seed_ratings": key[0],
                "algorithm": key[1],
                "status": status,
                "content_dependent": dependent,
                "max_abs_difference": worst,
                "historical": {m: old[m] for m in METRICS},
                "reproduced": {m: row[m] for m in METRICS},
            }
        )
    paired = {}
    for seeds, models in reproduced["paired_ndcg_vs_popularity_95"].items():
        paired[seeds] = {
            "historical": historical["paired_ndcg_vs_popularity_95"][seeds]["Adaptive"],
            "reproduced": models["Adaptive"],
        }
    return rows, paired


def markdown(document):
    comparison = document["comparison"]
    lines = [
        "# MovieLens 1M protocol 3 — reproduction",
        "",
        f"Generated: {document['generated_utc']} by `python -m scripts.reproduce_ml_v3` "
        f"in {document['seconds']:.0f} s. Recorded evidence: [ml_v3.json](ml_v3.json) "
        f"({document['historical_generated_utc']}).",
        "",
        "## Inputs",
        "",
        "| Input | Recorded | Reproduction | Same |",
        "|---|---|---|---|",
        f"| MovieLens 1M ZIP SHA-256 | `{document['dataset_sha256']['historical'][:12]}…` | "
        f"`{document['dataset_sha256']['reproduced'][:12]}…` | "
        f"{document['dataset_sha256']['historical'] == document['dataset_sha256']['reproduced']} |",
        f"| Content snapshot SHA-256 | `{(document['content_sha256']['historical'] or '-')[:12]}…` | "
        f"`{(document['content_sha256']['reproduced'] or '-')[:12]}…` | "
        f"{document['content_sha256']['historical'] == document['content_sha256']['reproduced']} |",
    ]
    for name, same in document["same_inputs"].items():
        lines.append(f"| {name} | | | {same} |")
    lines += [
        "",
        "## Selected policy (ALS, LSA, quality)",
        "",
        "| Seed ratings | Recorded | Reproduction |",
        "|---|---|---|",
    ]
    for seeds, weights in document["selected_policy"]["reproduced"].items():
        lines.append(
            f"| {seeds} | {document['selected_policy']['historical'][seeds]} | {weights} |"
        )
    lines += [
        "",
        f"## Recorded vs reproduced (tolerance {TOLERANCE:g})",
        "",
        "| Seeds | Model | NDCG@10 recorded | NDCG@10 reproduced | Max |Δ| (all metrics) | Status |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in comparison["results"]:
        lines.append(
            f"| {row['seed_ratings']} | {row['algorithm']} | "
            f"{row['historical']['ndcg@10']:.4f} | {row['reproduced']['ndcg@10']:.4f} | "
            f"{row['max_abs_difference']:.2e} | {row['status']} |"
        )
    lines += [
        "",
        "Paired Adaptive − Popularity NDCG@10, 95% interval:",
        "",
        "| Seeds | Recorded | Reproduced |",
        "|---:|---|---|",
    ]
    for seeds, pair in comparison["paired_adaptive_ndcg"].items():
        old, new = pair["historical"], pair["reproduced"]
        lines.append(
            f"| {seeds} | [{old[0]:+.4f}, {old[1]:+.4f}] | [{new[0]:+.4f}, {new[1]:+.4f}] |"
        )
    extended = document["bootstrap"]
    lines += [
        "",
        "## All metrics with 95% user-bootstrap intervals (reproduction)",
        "",
        f"{extended['3']['users']} test users, {extended['3']['resamples']} resamples, "
        f"seed {extended['3']['seed']}. Catalog coverage is shown without an interval: it is "
        "a union over users, not a per-user mean, so a with-replacement user bootstrap "
        "(~63% distinct users per resample) biases it downward and is not a valid interval.",
        "",
    ]
    for seeds, block in extended.items():
        lines += [
            f"### After {seeds} seed ratings",
            "",
            "| Model | Recall@10 | NDCG@10 | Coverage | Novelty (bits) | Diversity |",
            "|---|---|---|---|---|---|",
        ]
        values = {r["algorithm"]: r for r in document["results"] if str(r["seed_ratings"]) == seeds}
        for model, ci in block["confidence_95"].items():
            cells = [
                f"{values[model][m]:.4f} [{ci[m][0]:.4f}, {ci[m][1]:.4f}]"
                for m in ("recall@10", "ndcg@10")
            ]
            cells.append(f"{values[model]['coverage']:.4f}")
            cells += [
                f"{values[model][m]:.4f} [{ci[m][0]:.4f}, {ci[m][1]:.4f}]"
                for m in ("novelty_bits", "diversity")
            ]
            lines.append(f"| {model} | " + " | ".join(cells) + " |")
        lines += [
            "",
            "Paired difference vs Popularity, 95% interval:",
            "",
            "| Model | Recall@10 | NDCG@10 | Novelty (bits) | Diversity |",
            "|---|---|---|---|---|",
        ]
        for model, ci in block["paired_vs_popularity_95"].items():
            if model != "Popularity":
                cells = [
                    f"[{ci[m][0]:+.4f}, {ci[m][1]:+.4f}]"
                    for m in ("recall@10", "ndcg@10", "novelty_bits", "diversity")
                ]
                lines.append(f"| {model} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += [
        "## Scope",
        "",
        document["scope"],
        "",
        "Novelty and coverage are not accuracy. An interval that includes zero means no "
        "established difference. User ID lists are not stored here (MovieLens 1M may not "
        "be redistributed without permission); their SHA-256 is compared instead.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--no-fetch-content",
        action="store_true",
        help="fail instead of rebuilding a missing content snapshot",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    started = time.perf_counter()
    ensure_inputs(historical, fetch_content=not args.no_fetch_content)
    from scripts.benchmark_v3 import experiment  # after inputs exist

    reproduced, test_rows = experiment()
    bootstrap = {seeds: bootstrap_all_metrics(rows) for seeds, rows in test_rows.items()}
    results, paired = compare(historical, reproduced)
    ids = ("validation_user_ids", "test_user_ids")
    document = {
        key: value
        for key, value in reproduced.items()
        if key not in ids and key != "validation_trials"
    }
    document.update(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        historical_generated_utc=historical["generated_utc"],
        seconds=time.perf_counter() - started,
        dataset_sha256={
            "historical": historical["source"]["sha256"],
            "reproduced": reproduced["source"]["sha256"],
        },
        content_sha256={
            "historical": historical["metadata_sha256"],
            "reproduced": reproduced["metadata_sha256"],
        },
        user_ids_sha256={name: digest(reproduced[name]) for name in ids},
        same_inputs={
            "events / catalog / split": all(
                historical[k] == reproduced[k] for k in ("events", "catalog", "split")
            ),
            "validation users (IDs)": historical["validation_user_ids"]
            == reproduced["validation_user_ids"],
            "test users (IDs)": historical["test_user_ids"] == reproduced["test_user_ids"],
            "ALS parameters": historical["model"] == reproduced["model"],
        },
        selected_policy={
            "historical": historical["selected_policy"],
            "reproduced": reproduced["selected_policy"],
        },
        comparison={"tolerance": TOLERANCE, "results": results, "paired_adaptive_ndcg": paired},
        bootstrap=bootstrap,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "ml_v3_repro.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "ml_v3_repro.md").write_text(markdown(document), encoding="utf-8")
    for row in results:
        print(
            f"{row['seed_ratings']:>2} {row['algorithm']:<13} {row['status']:<27} "
            f"max|Δ|={row['max_abs_difference']:.2e}",
            flush=True,
        )
    print("Saved:", args.output_dir / "ml_v3_repro.json", flush=True)


if __name__ == "__main__":
    main()
