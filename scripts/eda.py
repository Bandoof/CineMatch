"""Create a reproducible dataset overview without redistributing raw ratings."""

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src.data import GENRES, ROOT, load_movielens  # noqa: E402
from src.catalog import latest_ratings  # noqa: E402


def analyze():
    movies, ratings = load_movielens()
    distinct = latest_ratings(ratings)
    summary = {"movies": len(movies), "users": int(ratings.user_id.nunique()),
               "ratings": len(ratings), "distinct_user_title_pairs": len(distinct),
               "mean_rating": float(ratings.rating.mean()),
               "density": len(distinct) / (len(movies) * ratings.user_id.nunique()),
               "min_timestamp": int(ratings.timestamp.min()),
               "max_timestamp": int(ratings.timestamp.max())}
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "eda.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
    ratings.rating.value_counts().sort_index().plot.bar(ax=axes[0], color="#f4ba68")
    axes[0].set(title="MovieLens 100K: rating distribution", xlabel="Rating", ylabel="Observations")
    movies[GENRES[1:]].sum().sort_values().plot.barh(ax=axes[1], color="#73aeb8")
    axes[1].set(title="Genres in the catalog", xlabel="Movies (multi-label)")
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    fig.savefig(assets / "dataset-overview.png", dpi=160)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    analyze()
