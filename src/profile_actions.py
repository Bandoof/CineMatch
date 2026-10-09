"""Session-state transitions without Streamlit, storage or model dependencies.

The UI boundary is a mutable mapping because Streamlit also stores widget values.
Catalog IDs and imported ratings must be validated before calling these actions.
"""

import math
from collections.abc import MutableMapping
from typing import Any

State = MutableMapping[str, Any]


def remember_change(state: State) -> None:
    """Copy the ranking inputs for ML Lab's before/after comparison."""
    state["recommendation_change"] = {
        "profile": dict(state["ratings"]),
        **{key: set(state[key]) for key in ("blocked", "topic_blocked", "snoozed", "watched")},
    }


def replace_profile(
    state: State,
    ratings: dict[int, float],
    blocked: set[int],
    demo: bool = False,
    not_seen: set[int] | None = None,
    watched: set[int] | None = None,
    watchlist: set[int] | None = None,
    topic_blocked: set[int] | None = None,
) -> None:
    """Replace a validated profile and clear widget values and transient undo state."""
    for key in list(state):
        if str(key).startswith("edit_"):
            del state[key]
    state["ratings"] = dict(ratings)
    state["blocked"] = set(blocked)
    state["topic_blocked"] = set(blocked if topic_blocked is None else topic_blocked)
    state["snoozed"] = set()
    state["demo"] = demo
    seen = set(watched or ()) | set(ratings)
    state["watched"] = seen
    state["not_seen"] = set(not_seen or ()) - seen
    state["watchlist"] = set(watchlist or ()) - seen
    for key in ("recommendation_change", "pending_seen", "last_uninterested"):
        state.pop(key, None)
    state["guide_history"] = []


def rate_title(state: State, mid: int, value: float) -> None:
    """Rate a catalog title; reject invalid values before any state mutation."""
    if isinstance(value, bool) or not math.isfinite(value) or not 0.5 <= value <= 5:
        raise ValueError("Rating must be a finite number between 0.5 and 5.")
    remember_change(state)
    state["ratings"][mid] = float(value)
    state["watched"].add(mid)
    state["not_seen"].discard(mid)
    state["watchlist"].discard(mid)


def mark_seen(state: State, mid: int, origin: str) -> None:
    """Exclude a watched title without inventing a star rating."""
    remember_change(state)
    state["pending_seen"] = {
        "mid": mid,
        "watched": mid in state["watched"],
        "later": mid in state["watchlist"],
        "not_seen": mid in state["not_seen"],
        "origin": origin,
    }
    state["watched"].add(mid)
    state["watchlist"].discard(mid)
    state["not_seen"].discard(mid)


def cancel_seen(state: State) -> None:
    """Restore pre-dialog membership; keep any rating made after the dialog opened."""
    previous = state.get("pending_seen")
    if previous is None:
        return
    remember_change(state)
    state.pop("pending_seen")
    mid = previous["mid"]
    if mid in state["ratings"]:
        return
    if not previous["watched"]:
        state["watched"].discard(mid)
    if previous["later"]:
        state["watchlist"].add(mid)
    if previous["not_seen"]:
        state["not_seen"].add(mid)


def undo_guide(state: State) -> None:
    """Undo the last guide answer without overwriting a later rating edit."""
    if not state["guide_history"]:
        return
    remember_change(state)
    previous = state["guide_history"].pop()
    mid, action, value = previous[:3]
    if action == "rating" and state["ratings"].get(mid) == value:
        state["ratings"].pop(mid)
        state["watched"].discard(mid)
        if len(previous) > 3 and previous[3]:
            state["watchlist"].add(mid)
        state.pop(f"edit_{mid}", None)
    elif action == "not_seen":
        state["not_seen"].discard(mid)
