"""Readable benchmark export from the same measured JSON used by the interface."""


def benchmark_markdown(report):
    columns = ("precision@10", "recall@10", "ndcg@10", "coverage", "diversity")
    lines = ["# Measured benchmark — protocol 2", "", report["protocol"], "",
             f"Canonical films: {report['canonical_films']}; source events: {report['source_rating_events']}.",
             "Latest available user/title ratings enter training only after splitting.",
             "Series are not evaluated here.", "",
             f"Hybrid alpha: **{report['selected_alpha']}**, selected by validation NDCG@10.", "",
             f"Warm test cohort: **{report['test_cohort']['evaluated_users']} users**.", "",
             "| Model | Precision@10 | Recall@10 | NDCG@10 | Coverage | Diversity |",
             "|---|---:|---:|---:|---:|---:|"]
    for model, row in report["metrics"].items():
        lines.append("| " + model + " | " + " | ".join(f"{row[key]:.4f}" for key in columns) + " |")
    lines += ["", "## 95% paired user bootstrap intervals", "",
              "1,000 samples, seed 42; identical user draws across models.", "",
              "| Model | NDCG@10 interval | NDCG minus Popularity interval |", "|---|---:|---:|"]
    for model in report["metrics"]:
        low, high = report["confidence_95"][model]["ndcg@10"]
        delta_low, delta_high = report["paired_ndcg_vs_popularity_95"][model]
        lines.append(f"| {model} | {low:.4f} – {high:.4f} | {delta_low:+.4f} – {delta_high:+.4f} |")
    lines += ["", "## New-user onboarding", "", report["onboarding"]["protocol"], "",
              f"Matched users: {report['onboarding']['users']}; background training users: "
              f"{report['onboarding']['training_users']}.", "",
              "| Seed ratings | Model | Recall@10 | NDCG@10 |", "|---:|---|---:|---:|"]
    for row in report["onboarding"]["results"]:
        lines.append(f"| {row['seed_ratings']} | {row['algorithm']} | "
                     f"{row['recall@10']:.4f} | {row['ndcg@10']:.4f} |")
    lines += ["", "## Fixed-cohort quality/variety analysis", "",
              "Default weight remains zero; test analysis does not select it.", "",
              "| MMR weight | NDCG@10 | Diversity | Coverage |", "|---:|---:|---:|---:|"]
    for row in report["diversity_analysis"]:
        lines.append(f"| {row['weight']} | {row['ndcg@10']:.4f} | "
                     f"{row['diversity']:.4f} | {row['coverage']:.4f} |")
    lines += ["", "Historical results do not guarantee live satisfaction or series quality.",
              "The full-data app model is never used by this evaluation."]
    return "\n".join(lines) + "\n"
