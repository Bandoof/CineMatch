"""Train the full-data app model. Evaluation uses separate temporal models."""

import json
import argparse

from src.collaborative import BiasedMF
from src.catalog import latest_ratings
from src.data import ROOT, fingerprint, load_app_movies, load_movielens


def train(expanded=False):
    movies, ratings = load_app_movies() if expanded else load_movielens()
    digest = fingerprint(movies, ratings)
    parameters = {}
    report_path = ROOT / "reports" / "expanded_metrics.json"
    if expanded and report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("fingerprint") == digest:
            parameters = {key: report["model"][key] for key in ("factors", "regularization")}
    model = BiasedMF(**parameters).fit(latest_ratings(ratings), movies.movie_id.to_numpy())
    target = "expanded" if expanded else "full"
    model.save(ROOT / "models" / f"{target}.npz", digest)
    (ROOT / "models" / f"{target}_training.json").write_text(json.dumps({
        "dataset": "MovieLens expanded" if expanded else "MovieLens 100K", "ratings": len(ratings), "movies": len(movies),
        "users": int(ratings.user_id.nunique()), "factors": model.factors,
        "epochs": model.epochs, "seed": model.random_state,
        "scope": "All observations; app only, never used for held-out evaluation",
    }, indent=2), encoding="utf-8")
    print(f"Trained full-data app model: models/{target}.npz")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--expanded", action="store_true")
    train(parser.parse_args().expanded)
