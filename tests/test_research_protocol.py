import numpy as np
import pandas as pd
import pytest

from src.research_protocol import (TargetUser, background, candidates, digest_json,
                                   summarize, targets, verify_boundaries, write_new_json)


def events(rows):
    return pd.DataFrame(rows, columns=["user_id", "movie_id", "rating", "timestamp"])


def test_target_selection_and_seeds_never_contain_future_or_old_users():
    past = events([(u, m, 1 + m % 5, m) for u in range(1, 8) for m in range(1, 22)])
    future = events([(u, 30, 5, 30) for u in range(1, 8)])
    selected = targets(past, future, {1, 2}, 3)
    assert len(selected) == 3
    assert {x.user_id for x in selected}.isdisjoint({1, 2})
    assert [x.user_id for x in selected] == [x.user_id for x in targets(past.sample(frac=1, random_state=3), future, {1, 2}, 3)]
    for user in selected:
        assert user.relevant == {30}
        assert user.history.timestamp.max() < 30
    train = background(past, {x.user_id for x in selected})
    assert set(train.user_id).isdisjoint(x.user_id for x in selected)


def test_future_seen_ratings_are_not_relevant_and_history_ties_are_stable():
    past = events([(1, 2, 3, 1), (1, 1, 4, 1)])
    future = events([(1, 1, 5, 2), (1, 3, 4, 2)])
    user = targets(past, future, set(), 2, minimum_history=2)[0]
    assert user.history.movie_id.tolist() == [1, 2]
    assert user.relevant == {3}


@pytest.mark.parametrize("bad", ["time", "overlap", "old"])
def test_leakage_boundaries_reject_invalid_protocol(bad):
    train, val, test = (events([(1, 1, 5, t)]) for t in (1, 2, 3))
    if bad == "time":
        val.timestamp = 1
    val_ids, test_ids, old_ids = [2], [3], {1}
    if bad == "overlap":
        test_ids = [2]
    if bad == "old":
        old_ids = {3}
    with pytest.raises(ValueError):
        verify_boundaries(train, val, test, val_ids, test_ids, old_ids)


def test_catalog_metrics_count_unavailable_labels_and_keep_same_candidates():
    ids = np.arange(1, 13)
    history = events([(1, 1, 5, 1), (1, 2, 4, 2)])
    users = [TargetUser(1, history, {2, 12, 99})]
    score = np.zeros(12)
    profile = {1: 5}
    assert candidates(ids, profile).tolist() == list(range(1, 12))
    result, rows, recommended = summarize(ids, users, [profile], [score], np.eye(12), np.zeros(12))
    assert recommended == [list(range(2, 12))]  # Stable ID ties, seed excluded.
    assert result["recall@10"] == 1 / 3  # Missing positive 99 remains in denominator.
    assert rows[0]["precision"] == .1
    assert result["past_seen_fraction@10"] == .1
    _, _, full = summarize(ids, users, [profile], [score], np.eye(12), np.zeros(12), full_history=True)
    assert full == [list(range(3, 13))]
    with pytest.raises(ValueError):
        summarize(ids, users, [profile], [np.full(12, np.nan)], np.eye(12), np.zeros(12))


def test_evidence_cannot_be_overwritten(tmp_path):
    path = tmp_path / "evidence.json"
    write_new_json(path, {"metric": .1})
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        write_new_json(path, {"metric": .9})
    assert path.read_bytes() == original
    assert digest_json({"a": 1, "b": 2}) == digest_json({"b": 2, "a": 1})
