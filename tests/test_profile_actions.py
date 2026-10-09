from copy import deepcopy

import pytest

from src import profile_actions as actions


def state():
    values = {}
    actions.replace_profile(values, {}, set())
    return values


def test_replace_copies_inputs_and_clears_widget_and_transient_values():
    values = state()
    values.update(edit_1=1, pending_seen={}, last_uninterested={}, guide_history=[(1, "rating", 5)])
    ratings, blocked = {1: 4.0}, {2}
    actions.replace_profile(values, ratings, blocked, not_seen={1, 3}, watchlist={1, 4})
    ratings[1] = 1
    blocked.clear()
    assert values["ratings"] == {1: 4}
    assert values["blocked"] == values["topic_blocked"] == {2}
    assert values["watched"] == {1}
    assert values["not_seen"] == {3}
    assert values["watchlist"] == {4}
    assert not values["guide_history"]
    assert not {"edit_1", "pending_seen", "last_uninterested"} & values.keys()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0, 6, True])
def test_invalid_rating_does_not_mutate_state(value):
    values = state()
    before = deepcopy(values)
    with pytest.raises(ValueError):
        actions.rate_title(values, 1, value)
    assert values == before


def test_snapshot_and_sessions_do_not_share_mutable_profile_values():
    first, second = state(), state()
    first["watchlist"].add(1)
    actions.rate_title(first, 1, 4)
    snapshot = deepcopy(first["recommendation_change"])
    actions.rate_title(second, 2, 5)
    first["ratings"][1] = 2
    first["watched"].add(3)
    assert first["recommendation_change"] == snapshot
    assert second["ratings"] == {2: 5}
    assert second["watched"] == {2}


def test_seen_cancel_restores_watchlist_and_unwatched_without_rating():
    values = state()
    values["watchlist"].add(1)
    values["not_seen"].add(1)
    actions.mark_seen(values, 1, "guide")
    assert values["watched"] == {1}
    assert not values["ratings"] and not values["watchlist"] and not values["not_seen"]
    actions.cancel_seen(values)
    assert not values["watched"]
    assert values["watchlist"] == values["not_seen"] == {1}
    actions.cancel_seen(values)  # Empty dialog is harmless.


def test_cancel_keeps_existing_seen_and_later_rating():
    values = state()
    values["watched"].add(1)
    actions.mark_seen(values, 1, "saved")
    actions.cancel_seen(values)
    assert values["watched"] == {1}
    actions.mark_seen(values, 2, "guide")
    actions.rate_title(values, 2, 4)
    actions.cancel_seen(values)
    assert values["watched"] == {1, 2}
    assert values["ratings"] == {2: 4}


def test_guide_undo_restores_watchlist_but_preserves_subsequent_rating_edit():
    values = state()
    values["watchlist"].add(1)
    values["guide_history"].append((1, "rating", 5, True))
    actions.rate_title(values, 1, 5)
    values["edit_1"] = 5
    actions.undo_guide(values)
    assert not values["ratings"] and not values["watched"]
    assert values["watchlist"] == {1}
    assert "edit_1" not in values
    values["guide_history"].append((2, "rating", 5, False))
    actions.rate_title(values, 2, 5)
    actions.rate_title(values, 2, 3)
    actions.undo_guide(values)
    assert values["ratings"] == {2: 3}
    assert values["watched"] == {2}
    values["not_seen"].add(3)
    values["guide_history"].append((3, "not_seen", None))
    actions.undo_guide(values)
    assert not values["not_seen"]
    actions.undo_guide(values)
