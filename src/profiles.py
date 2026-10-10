"""Validated, versioned profile interchange and explicit local SQLite storage."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

MAX_PROFILE_BYTES = 1_000_000


def parse_profile(payload, max_bytes=MAX_PROFILE_BYTES):
    """Reject ambiguous JSON and parser exhaustion without changing user state."""
    if isinstance(payload, bytes):
        if len(payload) > max_bytes:
            raise ValueError("Profile is too large.")
        payload = payload.decode("utf-8")
    if not isinstance(payload, str) or len(payload.encode("utf-8")) > max_bytes:
        raise ValueError("Profile is too large or is not UTF-8 JSON.")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON keys are not allowed.")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-finite JSON numbers are not allowed.")

    try:
        document = json.loads(payload, object_pairs_hook=unique_object,
                              parse_constant=invalid_constant)
    except RecursionError as error:
        raise ValueError("Profile nesting is too deep.") from error
    if not isinstance(document, dict):
        raise ValueError("A profile must be a JSON object.")
    return document


def export_profile(engine, ratings, blocked, not_seen=None, watched=None, watchlist=None, topic_blocked=None):
    ratings = engine.validate_profile(ratings)
    hidden = sorted({engine.normalize_id(mid) for mid in blocked})
    records = []
    for mid, rating in sorted(ratings.items()):
        row = engine.movies.iloc[engine.positions[mid]]
        records.append({"item_id": mid, "rating": rating, "title": row.title,
                        "media_type": row.media_type, "source": row.source})
    seen = {engine.normalize_id(mid) for mid in (watched or [])} | set(ratings)
    skipped = sorted({engine.normalize_id(mid) for mid in (not_seen or [])} - seen)
    later = sorted({engine.normalize_id(mid) for mid in (watchlist or [])} - seen)
    topics = sorted({engine.normalize_id(mid) for mid in (blocked if topic_blocked is None else topic_blocked)})
    if not set(topics) <= set(hidden):
        raise ValueError("Topic feedback must refer to dismissed titles.")
    document = {"schema_version": 5, "app": "CineMatch", "ratings": records, "topic_blocked": topics,
                "blocked": hidden, "not_seen": skipped, "watched": sorted(seen), "watchlist": later}
    if hasattr(engine, "export_references"):
        references = engine.export_references(set(ratings) | set(hidden) | set(skipped) | seen | set(later))
        if references:
            document.update(schema_version=6, catalog_refs=references)
    return json.dumps(document, ensure_ascii=False, indent=2)


def import_profile(engine, payload):
    ratings, hidden, _ = import_discovery_profile(engine, payload)
    return ratings, hidden


def import_discovery_profile(engine, payload):
    ratings, hidden, not_seen, _, _ = import_library_profile(engine, payload)
    return ratings, hidden, not_seen


def import_library_profile(engine, payload):
    document = parse_profile(payload)
    candidate = engine
    if document.get("schema_version") == 6:
        if not hasattr(engine, "with_references"):
            raise ValueError("This catalog cannot restore provider references.")
        candidate = engine.with_references(document.get("catalog_refs"))
    result = _import_library_document(candidate, document)
    # Commit restored identities only after the entire profile validates.
    if candidate is not engine:
        engine.adopt_references(candidate)
    return result


def _import_library_document(engine, document):
    if "schema_version" not in document:
        # Compatibility with the original {"movie_id": rating} export.
        ratings = engine.validate_profile(document)
        return ratings, set(), set(), set(ratings), set()
    if document["schema_version"] not in (2, 3, 4, 5, 6) or document.get("app") != "CineMatch":
        raise ValueError("Unsupported profile schema.")
    rows, blocked = document.get("ratings"), document.get("blocked", [])
    skipped = document.get("not_seen", []) if document["schema_version"] >= 3 else []
    watched = document.get("watched", []) if document["schema_version"] >= 4 else []
    watchlist = document.get("watchlist", []) if document["schema_version"] >= 4 else []
    if any(not isinstance(values, list) or len(values) > 5000
           for values in (rows, blocked, skipped, watched, watchlist)):
        raise ValueError("Invalid profile structure.")
    ratings = {}
    for record in rows:
        if not isinstance(record, dict) or "item_id" not in record or "rating" not in record:
            raise ValueError("Every profile entry needs item_id and rating.")
        canonical = engine.normalize_id(record["item_id"])
        checked = engine.validate_profile({canonical: record["rating"]})[canonical]
        if canonical in ratings and ratings[canonical] != checked:
            raise ValueError("Conflicting ratings for the same canonical title.")
        ratings[canonical] = checked
    hidden = {engine.normalize_id(mid) for mid in blocked}
    seen = {engine.normalize_id(mid) for mid in watched} | set(ratings)
    not_seen = {engine.normalize_id(mid) for mid in skipped} - seen
    later = {engine.normalize_id(mid) for mid in watchlist} - seen
    _import_topics_document(engine, document)
    return ratings, hidden, not_seen, seen, later


def import_topics(engine, payload):
    document = parse_profile(payload)
    if document.get("schema_version") == 6:
        if not hasattr(engine, "with_references"):
            raise ValueError("This catalog cannot restore provider references.")
        engine = engine.with_references(document.get("catalog_refs"))
    return _import_topics_document(engine, document)


def _import_topics_document(engine, document):
    if "schema_version" not in document:
        return set()
    values = document.get("topic_blocked", document.get("blocked", []))
    if not isinstance(values, list) or len(values) > 5000:
        raise ValueError("Invalid topic feedback.")
    topics = {engine.normalize_id(mid) for mid in values}
    if not topics <= {engine.normalize_id(mid) for mid in document.get("blocked", [])}:
        raise ValueError("Invalid topic feedback references.")
    return topics


class ProfileStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS profiles "
                                   "(name TEXT PRIMARY KEY, payload TEXT NOT NULL, "
                                   "updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
                yield connection
        finally:
            connection.close()

    def names(self):
        with self.connect() as connection:
            return [row[0] for row in connection.execute("SELECT name FROM profiles ORDER BY name")]

    def save(self, name, payload):
        name = name.strip()
        if not name or len(name) > 80 or len(payload.encode("utf-8")) > MAX_PROFILE_BYTES:
            raise ValueError("Invalid profile name or size.")
        with self.connect() as connection:
            connection.execute("INSERT INTO profiles(name,payload) VALUES (?,?) "
                               "ON CONFLICT(name) DO UPDATE SET payload=excluded.payload, "
                               "updated=CURRENT_TIMESTAMP", (name, payload))

    def load(self, name):
        with self.connect() as connection:
            row = connection.execute("SELECT payload FROM profiles WHERE name=?", (name,)).fetchone()
        if row is None:
            raise ValueError("Saved profile no longer exists.")
        return row[0]
