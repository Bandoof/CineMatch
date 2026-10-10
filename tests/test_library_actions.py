import json

import numpy as np
import pytest

from app.recommender import Recommender
from src.catalog_view import CatalogView
from src.library_actions import change, undo
from src.modern_catalog import CatalogTitle, ModernCatalog
from src.profiles import export_profile, import_library_profile


def state():
    return {
        "ratings": {},
        **{
            key: set()
            for key in ("blocked", "topic_blocked", "snoozed", "watched", "watchlist", "not_seen")
        },
    }


def test_library_actions_are_reversible_and_seen_is_explicit():
    values = state()
    change(values, 1, "watchlist")
    assert values["watchlist"] == {1} and not values["watched"]
    change(values, 1, "rate", 4.5)
    assert values["ratings"] == {1: 4.5} and values["watched"] == {1} and not values["watchlist"]
    undo(values)
    assert values["watchlist"] == {1} and not values["ratings"] and not values["watched"]
    change(values, 2, "watched")
    assert 2 in values["watched"] and 2 not in values["ratings"]
    change(values, 3, "hide")
    assert values["blocked"] == values["topic_blocked"] == {3}
    undo(values)
    assert not values["blocked"] and not values["topic_blocked"]
    change(values, 3, "snooze")
    assert values["snoozed"] == {3}
    change(values, 4, "not_seen")
    assert values["not_seen"] == {4} and 4 not in values["ratings"]


def test_invalid_rating_preserves_last_undo():
    values = state()
    change(values, 1, "watchlist")
    previous = values["library_undo"]
    with pytest.raises(ValueError):
        change(values, 1, "rate", float("nan"))
    assert values["library_undo"] is previous and values["watchlist"] == {1}


def test_unwatch_never_erases_ratings_and_undo_restores_activity():
    values = state()
    change(values, 1, "watchlist")
    first_activity = dict(values["session_activity"])
    change(values, 2, "watched")
    undo(values)
    assert values["session_activity"] == first_activity and not values["watched"]
    change(values, 1, "rate", 4)
    change(values, 1, "unwatch")
    assert values["ratings"] == {1: 4} and values["watched"] == {1}
    change(values, 1, "remove_rating")
    change(values, 1, "unwatch")
    assert not values["ratings"] and not values["watched"]
    undo(values)
    assert values["watched"] == {1}


def test_modern_profile_roundtrip_and_old_schemas_keep_format(sample):
    base = Recommender(*sample)
    title = CatalogTitle(
        "TMDB", 90, "Movie", "Synthetic Modern", title_uk="Синтетична назва", genres=("Drama",)
    )
    view = CatalogView(base, ModernCatalog([title]))
    mid = title.canonical_id
    payload = export_profile(view, {1: 4, mid: 5}, {2}, watched={mid}, watchlist={3})
    assert json.loads(payload)["schema_version"] == 6
    fresh = CatalogView(base)
    assert import_library_profile(fresh, payload) == ({1: 4.0, mid: 5.0}, {2}, set(), {1, mid}, {3})
    assert fresh.reference_only == {mid}
    assert json.loads(export_profile(view, {1: 4}, set()))["schema_version"] == 5
    expected = base.score_components({1: 4})
    for key, values in base.score_components(fresh.known_profile({1: 4, mid: 5})).items():
        np.testing.assert_array_equal(values, expected[key])


@pytest.mark.parametrize(
    "change_document",
    [
        lambda d: d.update(topic_blocked=[999]),
        lambda d: d["ratings"].append({"item_id": 999, "rating": 5}),
        lambda d: d["ratings"].append({"item_id": -101, "rating": 1}),
        lambda d: d["catalog_refs"]["-101"].update(provider_id=102),
        lambda d: d["catalog_refs"]["-101"].update(poster_url="https://example.com/private"),
    ],
)
def test_failed_modern_import_never_changes_catalog_or_profile(sample, change_document):
    base = Recommender(*sample)
    title = CatalogTitle("TVmaze", 101, "Series", "Synthetic Identity")
    payload = json.loads(
        export_profile(CatalogView(base, ModernCatalog([title])), {-101: 5}, set())
    )
    change_document(payload)
    view = CatalogView(base)
    with pytest.raises(ValueError):
        import_library_profile(view, json.dumps(payload))
    assert -101 not in view.positions and not view.reference_only
