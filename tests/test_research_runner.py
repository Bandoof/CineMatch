import json

import numpy as np
import pandas as pd
import pytest

from app.recommender import Recommender
from scripts.research_v12 import blend_grid, verify_selection
from src.research_onboarding import simulate
from src.research_protocol import TargetUser, digest_json, file_digest, source_fingerprint
from src.semantic import SemanticContent


def test_source_or_manifest_change_blocks_final_before_access(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    source = "src/research_models.py"
    from src.data import ROOT

    selection = {
        "manifest_sha256": file_digest(manifest),
        "source_paths": [source],
        "source_sha256": source_fingerprint(ROOT, [source]),
        "embedding_artifact_sha256": None,
    }
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(selection), encoding="utf-8")
    assert verify_selection(tmp_path) == selection
    selection["source_sha256"] = digest_json("different numerical source")
    path.write_text(json.dumps(selection), encoding="utf-8")
    with pytest.raises(ValueError, match="source changed"):
        verify_selection(tmp_path)
    assert not (tmp_path / "final-access.json").exists()
    selection["source_sha256"] = source_fingerprint(ROOT, [source])
    path.write_text(json.dumps(selection), encoding="utf-8")
    manifest.write_text('{"changed":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="manifest changed"):
        verify_selection(tmp_path)


def test_blend_grid_is_fixed_nonnegative_and_includes_baselines():
    grid = blend_grid(10)
    assert len(grid) == 66
    assert (1, 0, 0) in grid and (0, 1, 0) in grid and (0, 0, 1) in grid
    assert all(min(weights) >= 0 and sum(weights) == pytest.approx(1) for weights in grid)


@pytest.mark.parametrize(
    "strategy", ["recent", "recognition", "familiar", "genre_diverse", "content_diverse"]
)
def test_onboarding_only_reveals_past_ratings_and_ignores_future_labels(sample, strategy):
    movies, ratings = sample
    engine = Recommender(movies, ratings)
    engine.attach_content(SemanticContent(engine.movies, dimensions=2))
    history = ratings[ratings.user_id == ratings.user_id.iloc[0]].copy()
    # Use the full catalog subset actually rated by this fixture user.
    maximum = min(3, history.movie_id.nunique())
    counts = tuple(range(1, maximum + 1))
    first = TargetUser(99, history, {9999})
    second = TargetUser(99, history, set())
    profiles, costs = simulate(engine, first, strategy, counts)
    other, _ = simulate(engine, second, strategy, counts)
    assert profiles == other
    observed = dict(zip(history.movie_id, history.rating))
    for n, profile in profiles.items():
        assert len(profile) == n
        assert all(observed[mid] == value for mid, value in profile.items())
        assert n <= costs[n] <= len(movies)
    assert np.isfinite(engine.score_components(profiles[maximum])["Adaptive"]).all()


def test_small_synthetic_validation_final_pipeline_and_exclusive_holdout(tmp_path, monkeypatch):
    """Exercise the real selection/blend/final paths without downloading any data."""
    from scripts import research_v12 as runner
    from src.data import ROOT

    config = json.loads((ROOT / "configs/ml-v12-2026-10-09.json").read_text(encoding="utf-8"))
    config.update(
        factors=[2],
        regularization=[1],
        additional_bias_regularization=[],
        fold_in_regularization=[1],
        epochs=2,
        bootstrap_resamples=30,
        blend_denominator=2,
    )
    manifest = {"config": config, "config_sha256": digest_json(config)}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    movies = pd.DataFrame(
        {
            "movie_id": range(1, 36),
            "title": [f"Synthetic {i}" for i in range(1, 36)],
            "year": 1995,
            "genres": [("Action",) if i % 2 else ("Comedy",) for i in range(1, 36)],
        }
    )
    ratings = pd.DataFrame(
        [(u, m, 1 + (u + m) % 5, m) for u in range(1, 8) for m in range(1, 26)],
        columns=["user_id", "movie_id", "rating", "timestamp"],
    )
    users = [
        TargetUser(
            u,
            pd.DataFrame(
                [(u, m, 1 + (u + m) % 5, m) for m in range(1, 21)], columns=ratings.columns
            ),
            {31, 32},
        )
        for u in (100, 101)
    ]
    monkeypatch.setattr(runner, "load_inputs", lambda *args: (manifest, movies, ratings, users))
    selection = runner.validate(tmp_path, tmp_path, None)
    assert selection["available_content_models"] == ["tfidf", "lsa64"]
    assert selection["content_costs"]["embedding_unavailable"]
    result = runner.final(tmp_path, tmp_path)
    assert result["test_users"] == 2
    assert len(result["onboarding"]) == 25
    assert all(0 <= row["ndcg@10"] <= 1 for row in result["results"])
    original = (tmp_path / "final.json").read_bytes()
    with pytest.raises(FileExistsError):
        runner.final(tmp_path, tmp_path)
    assert (tmp_path / "final.json").read_bytes() == original
