"""Reversible library changes, independent of rendering and persistence."""

from datetime import datetime, timezone

from src.profile_actions import rate_title, remember_change

SETS = ("blocked", "topic_blocked", "snoozed", "watched", "watchlist", "not_seen")


def change(state, mid, action, rating=None):
    if action not in (
        "rate",
        "watchlist",
        "watched",
        "hide",
        "snooze",
        "not_seen",
        "remove_rating",
        "unwatch",
    ):
        raise ValueError("Unknown library action.")
    previous = {
        "ratings": dict(state["ratings"]),
        "session_activity": dict(state.get("session_activity", {})),
        **{key: set(state[key]) for key in SETS},
    }
    # Invalid ratings must fail before replacing the previous Undo record.
    if action == "rate":
        rate_title(state, mid, rating)
    else:
        remember_change(state)
        if action == "watchlist":
            if mid in state["watchlist"]:
                state["watchlist"].remove(mid)
            elif mid not in state["watched"]:
                state["watchlist"].add(mid)
        elif action == "watched":
            state["watched"].add(mid)
            state["watchlist"].discard(mid)
            state["not_seen"].discard(mid)
        elif action == "hide":
            if mid in state["blocked"]:
                state["blocked"].remove(mid)
                state["topic_blocked"].discard(mid)
            else:
                state["blocked"].add(mid)
                state["topic_blocked"].add(mid)
        elif action == "snooze":
            state["snoozed"].symmetric_difference_update({mid})
        elif action == "not_seen":
            if mid not in state["watched"]:
                state["not_seen"].add(mid)
        elif action == "remove_rating":
            state["ratings"].pop(mid, None)
        elif action == "unwatch":
            if mid not in state["ratings"]:
                state["watched"].discard(mid)
    state["library_undo"] = previous
    activity = dict(state.get("session_activity", {}))
    activity[mid] = datetime.now(timezone.utc).isoformat()
    state["session_activity"] = dict(sorted(activity.items(), key=lambda p: p[1])[-100:])


def undo(state):
    previous = state.pop("library_undo", None)
    if previous is not None:
        remember_change(state)
        state.update(previous)
