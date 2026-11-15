"""Metric correctness on small hand-computed examples (Stage 2 ML foundation)."""

import json
import math

import numpy as np
import pytest

from scripts.reproduce_ml_v3 import compare, content_dependent
from src.data import ROOT
from src.evaluation import (
    bootstrap_all_metrics,
    bootstrap_intervals,
    catalog_coverage,
    novelty_bits,
    ranking_metrics,
)
from src.ml_config import model_parameters

TOP10 = list(range(1, 11))


def test_ranking_metrics_hit_at_first_position():
    assert ranking_metrics(TOP10, {1}) == {"precision": 0.1, "recall": 1.0, "ndcg": 1.0}


def test_ranking_metrics_hit_at_last_position_is_discounted():
    result = ranking_metrics(TOP10, {10})
    assert result["recall"] == 1.0
    assert result["ndcg"] == pytest.approx(1 / math.log2(11))


def test_ranking_metrics_partial_hits_against_ideal_order():
    # Two relevant items, only the second one is recommended (at rank 2).
    result = ranking_metrics(TOP10, {2, 99})
    assert result["precision"] == pytest.approx(0.1)
    assert result["recall"] == pytest.approx(0.5)
    assert result["ndcg"] == pytest.approx((1 / math.log2(3)) / (1 + 1 / math.log2(3)))


def test_ranking_metrics_more_relevant_than_k_caps_ideal_dcg():
    result = ranking_metrics(TOP10, set(range(1, 13)))
    assert result == {"precision": 1.0, "recall": pytest.approx(10 / 12), "ndcg": 1.0}


def test_ranking_metrics_miss_and_invalid_input():
    assert ranking_metrics(TOP10, {42}) == {"precision": 0.0, "recall": 0.0, "ndcg": 0.0}
    with pytest.raises(ValueError):
        ranking_metrics(TOP10, set())


def test_novelty_bits_is_mean_self_information():
    assert novelty_bits([0.5, 0.25]) == pytest.approx(1.5)
    assert novelty_bits([1.0]) == 0.0
    with pytest.raises(ValueError):
        novelty_bits([0.0])


def test_catalog_coverage_counts_distinct_items():
    assert catalog_coverage([(1, 2), (2, 3)], 10) == pytest.approx(0.3)
    with pytest.raises(ValueError):
        catalog_coverage([(1,)], 0)


def rows(ndcg_values, novelty=2.0):
    return [
        {"precision": v / 10, "recall": v, "ndcg": v, "novelty_bits": novelty, "diversity": 0.5}
        for v in ndcg_values
    ]


def test_bootstrap_identical_models_have_zero_paired_difference():
    users = rows([0.0, 0.2, 0.9, 0.4])
    result = bootstrap_all_metrics({"Popularity": users, "Adaptive": list(users)}, resamples=50)
    for interval in result["paired_vs_popularity_95"]["Adaptive"].values():
        assert interval == [0.0, 0.0]


def test_bootstrap_constant_metric_has_degenerate_interval():
    result = bootstrap_all_metrics({"Popularity": rows([0.3, 0.3, 0.3])}, resamples=50)
    ci = result["confidence_95"]["Popularity"]
    assert ci["ndcg@10"] == pytest.approx([0.3, 0.3])
    assert ci["novelty_bits"] == pytest.approx([2.0, 2.0])
    assert "coverage" not in ci  # a union over users has no valid user-bootstrap interval


def test_resampled_coverage_is_biased_so_it_gets_no_interval():
    # 100 users, each recommending one distinct item: full coverage is 100/100.
    lists = [(i,) for i in range(100)]
    draws = np.random.default_rng(42).integers(0, 100, (200, 100))
    resampled = [catalog_coverage([lists[i] for i in draw], 100) for draw in draws]
    assert catalog_coverage(lists, 100) == 1.0
    assert max(resampled) < 0.8  # ~63% distinct users: the interval would exclude 1.0


def test_bootstrap_uses_the_same_draws_as_the_recorded_protocol():
    per_user = {
        "Popularity": rows([0.0, 0.1, 0.5, 0.2, 0.9]),
        "Adaptive": rows([0.3, 0.0, 0.6, 0.2, 0.7]),
    }
    old_intervals, old_paired = bootstrap_intervals(per_user)
    new = bootstrap_all_metrics(per_user)
    assert new["confidence_95"]["Adaptive"]["ndcg@10"] == old_intervals["Adaptive"]["ndcg@10"]
    assert new["paired_vs_popularity_95"]["Adaptive"]["ndcg@10"] == old_paired["Adaptive"]
    assert bootstrap_all_metrics(per_user) == new  # fixed seed
    with pytest.raises(ValueError):
        bootstrap_all_metrics({"Popularity": rows([0.1]), "Adaptive": rows([0.1, 0.2])})


def test_benchmark_config_matches_the_recorded_v3_model():
    recorded = json.loads((ROOT / "reports/ml_v3.json").read_text(encoding="utf-8"))["model"]
    benchmark = model_parameters("benchmark_1m")
    assert {k: benchmark[k] for k in recorded} == recorded
    demo = model_parameters("demo_pack")
    assert demo["factors"] <= 24  # src/portfolio.py rejects larger demo models
    with pytest.raises(ValueError):
        model_parameters("unknown")


def test_reproduction_comparison_labels_content_dependent_differences():
    metrics = {
        m: 0.1
        for m in ("precision@10", "recall@10", "ndcg@10", "coverage", "diversity", "novelty_bits")
    }
    policy = {"3": [0.25, 0.25, 0.5], "5": [0, 0, 1.0], "10": [0, 0, 1.0]}
    names = ("Popularity", "Collaborative", "Semantic", "Adaptive")
    historical = {
        "selected_policy": policy,
        "results": [{"seed_ratings": 3, "algorithm": n, **metrics} for n in names],
        "paired_ndcg_vs_popularity_95": {"3": {"Adaptive": [0.0, 0.1]}},
    }
    changed = {**metrics, "ndcg@10": 0.2}
    reproduced = {
        "selected_policy": policy,
        "results": [
            {"seed_ratings": 3, "algorithm": n, **(metrics if n == "Popularity" else changed)}
            for n in names
        ],
        "paired_ndcg_vs_popularity_95": {"3": {"Adaptive": [0.0, 0.2]}},
    }
    results, paired = compare(historical, reproduced)
    status = {r["algorithm"]: r["status"] for r in results}
    assert status == {
        "Popularity": "match",
        "Collaborative": "differs",
        "Semantic": "differs (content snapshot)",
        "Adaptive": "differs (content snapshot)",
    }
    assert paired["3"] == {"historical": [0.0, 0.1], "reproduced": [0.0, 0.2]}
    assert not content_dependent("Adaptive", "5", historical, reproduced)
