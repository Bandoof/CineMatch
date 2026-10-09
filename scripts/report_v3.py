"""Create a measured markdown report and exportable plot from the recorded run."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.data import ROOT  # noqa: E402


def run():
    report = json.loads((ROOT / "reports/ml_v3.json").read_text(encoding="utf-8"))
    lines = ["# Independent MovieLens 1M experiment", "",
             f"Generated: {report['generated_utc']}. Protocol 3. {report['events']:,} events / "
             f"{report['source_users']:,} source users / {report['catalog']:,} canonical films.", "",
             f"Validation: {report['validation_users']} users. Test: {report['test_users']} users. "
             f"User overlap across distinct time boundaries: {report['validation_test_user_overlap']}.", "",
             "Weights selected on validation only. Values below are untouched test results.", "",
             "![NDCG with 95% user bootstrap intervals](../assets/ml-v3-ndcg.png)", "",
             "| Seed ratings | ALS | LSA | Community quality |", "|---|---:|---:|---:|"]
    for count, weights in report["selected_policy"].items():
        lines.append(f"| {count} | {weights[0]:.0%} | {weights[1]:.0%} | {weights[2]:.0%} |")
    for count in (3, 5, 10):
        lines += ["", f"## After {count} seed ratings", "",
                  "| Model | Precision@10 | Recall@10 | NDCG@10 | Coverage | Diversity | Novelty (bits) |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for row in report["results"]:
            if row["seed_ratings"] == count:
                numbers = " | ".join(f"{row[k]:.4f}" for k in
                                     ("precision@10", "recall@10", "ndcg@10", "coverage", "diversity", "novelty_bits"))
                lines.append(f"| {row['algorithm']} | {numbers} |")
        low, high = report["paired_ndcg_vs_popularity_95"][str(count)]["Adaptive"]
        lines += ["", f"Paired Adaptive − Popularity NDCG@10 95% interval: [{low:+.4f}, {high:+.4f}]. "
                  + ("Positive improvement in this cohort." if low > 0 else "No established improvement over popularity.")]
    lines += ["", "## Scope", "", report["scope"], "",
              "These are separate 1M experiment numbers. The application transfers the mixing "
              "policy to another catalog; these are not application/series accuracy claims. "
              "Novelty is not accuracy. Confidence intervals do not cover deployment shift.", "",
              "## Reproduce", "", "```bash", "python -m scripts.download_content",
              "python -m scripts.download_benchmark", "python -m scripts.benchmark_v3",
              "python -m scripts.report_v3", "```", "",
              f"MovieLens ZIP SHA-256: `{report['source']['sha256']}`.", "",
              f"Content snapshot SHA-256: `{report['metadata_sha256']}`.", "",
              "[Model card](../docs/ml-v3-model-card.md) · [JSON](ml_v3.json) · [CSV](ml_v3.csv) · "
              "[Official dataset](https://grouplens.org/datasets/movielens/1m/)"]
    (ROOT / "reports/ml_v3.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    names = ["Popularity", "Collaborative", "Semantic", "Genres", "Adaptive"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True, layout="constrained")
    maximum = max(values["ndcg@10"][1] for interval in report["confidence_95"].values() for values in interval.values())
    for ax, count in zip(axes, (3, 5, 10)):
        rows = {r["algorithm"]: r for r in report["results"] if r["seed_ratings"] == count}
        values = [rows[name]["ndcg@10"] for name in names]
        intervals = [report["confidence_95"][str(count)][name]["ndcg@10"] for name in names]
        errors = [[max(0, v-b[0]) for v, b in zip(values, intervals)],
                  [max(0, b[1]-v) for v, b in zip(values, intervals)]]
        ax.bar(names, values, color=["#9a9ea8", "#17253a", "#497eae", "#c1ac8c", "#e84f3e"], yerr=errors, capsize=3)
        ax.set_title(f"{count} seed ratings")
        ax.tick_params(axis="x", rotation=45)
        ax.set_ylim(0, maximum*1.15)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.18)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("NDCG@10")
    fig.suptitle(f"MovieLens 1M · {report['test_users']} test users · 95% user bootstrap intervals")
    fig.savefig(ROOT / "assets/ml-v3-ndcg.png", dpi=150)
    plt.close(fig)
    print("Measured report and figure saved.")


if __name__ == "__main__":
    run()
