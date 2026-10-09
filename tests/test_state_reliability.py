import json

import numpy as np
import pytest

from app.recommender import Recommender
from src.memory import MemoryConflict, MemoryStore
from src.profiles import ProfileStore, export_profile, import_library_profile


@pytest.mark.parametrize(
    "payload", ['{"version":1,"version":1}', '{"value":NaN}', "[" * 2000 + "]" * 2000]
)
def test_corrupt_memory_is_rejected_and_not_rewritten(tmp_path, payload):
    store = MemoryStore(tmp_path / "test.sqlite3")
    store.read()
    with store.connect() as connection:
        connection.execute("INSERT INTO current_memory VALUES (1,1,?)", (payload,))
    with pytest.raises(ValueError):
        store.read()
    with store.connect() as connection:
        assert connection.execute("SELECT document FROM current_memory").fetchone()[0] == payload


def test_transaction_failure_rolls_back_and_store_recovers(tmp_path):
    store = ProfileStore(tmp_path / "test.sqlite3")
    store.save("kept", "original")
    with pytest.raises(RuntimeError):
        with store.connect() as connection:
            connection.execute("UPDATE profiles SET payload=? WHERE name=?", ("wrong", "kept"))
            raise RuntimeError("synthetic interruption")
    assert store.load("kept") == "original"
    # A quoted name is data, not SQL; normal writes recover after rollback.
    name = "x'); DROP TABLE profiles; --"
    store.save(name, "new")
    assert store.load(name) == "new"
    assert store.load("kept") == "original"


def test_two_installation_stores_and_stale_writer_are_isolated(tmp_path):
    first, second = [MemoryStore(tmp_path / name) for name in ("a.sqlite3", "b.sqlite3")]
    first.read()
    second.read()
    document = {"version": 1, "enabled": False, "profile": "", "preferences": {}}
    first.write(document, 0)
    assert second.read() == (0, None)
    with pytest.raises(MemoryConflict):
        first.write({**document, "enabled": True}, 0)
    assert first.read() == (1, document)


@pytest.mark.parametrize("version", [2, 3, 4, 5])
def test_old_profiles_roundtrip_to_current_schema(sample, version):
    engine = Recommender(*sample)
    payload = json.dumps(
        {
            "schema_version": version,
            "app": "CineMatch",
            "ratings": [{"item_id": 1, "rating": 4}],
            "blocked": [2],
        }
    )
    ratings, blocked, skipped, seen, later = import_library_profile(engine, payload)
    restored = import_library_profile(
        engine, export_profile(engine, ratings, blocked, skipped, seen, later)
    )
    assert restored == (ratings, blocked, skipped, seen, later)
    assert seen == {1}


def test_cached_arrays_and_profiles_are_isolated(sample):
    engine = Recommender(*sample)
    first = engine.score_components({1: 5})
    expected = {name: values.copy() for name, values in first.items()}
    for values in first.values():
        values[:] = -999
    second = engine.score_components({2: 1})
    for name, values in engine.score_components({1: 5}).items():
        np.testing.assert_array_equal(values, expected[name])
        assert not np.shares_memory(values, second[name])
