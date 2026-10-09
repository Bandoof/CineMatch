"""Local installation memory, independent of explicitly named profiles."""

import json
import math

from src.profiles import MAX_PROFILE_BYTES, ProfileStore


class MemoryConflict(ValueError):
    """A different browser session saved a newer state."""


def preferences(values):
    """Only restore known UI values; never inject arbitrary widget/session keys."""
    clean = {}
    options = {"ui_language": {"uk", "en"}, "media_type": {"All", "Movie", "Series"},
               "algorithm": {"Adaptive", "Semantic", "Hybrid", "Collaborative", "Item-KNN", "Content-based", "Popularity"}}
    for key, allowed in options.items():
        if isinstance(values.get(key), str) and values[key] in allowed:
            clean[key] = values[key]
    for key in ("posters", "localized_only_pref"):
        if isinstance(values.get(key), bool):
            clean[key] = values[key]
    if type(values.get("minimum")) is int and values["minimum"] in (0, 1, 5, 10, 20, 50):
        clean["minimum"] = values["minimum"]
    diversity = values.get("diversity")
    if type(diversity) in (float, int) and math.isfinite(diversity) and 0 <= diversity <= 1:
        clean["diversity"] = float(diversity)
    years = values.get("years")
    if isinstance(years, (list, tuple)) and len(years) == 2 and all(type(y) is int for y in years):
        if 1800 <= years[0] <= years[1] <= 2200:
            clean["years"] = tuple(years)
    genres = values.get("genres")
    if isinstance(genres, list) and len(genres) <= 100 and all(isinstance(g, str) and len(g) <= 80 for g in genres):
        clean["genres"] = genres
    return clean


class MemoryStore(ProfileStore):
    def read(self):
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS current_memory "
                               "(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, document TEXT NOT NULL)")
            row = connection.execute("SELECT revision,document FROM current_memory WHERE id=1").fetchone()
        if row is None:
            return 0, None
        if len(row[1].encode("utf-8")) > MAX_PROFILE_BYTES + 20000:
            raise ValueError("Invalid local memory size.")
        document = json.loads(row[1])
        if (not isinstance(document, dict) or document.get("version") != 1
                or type(document.get("enabled")) is not bool
                or not isinstance(document.get("profile"), str)
                or not isinstance(document.get("preferences"), dict)):
            raise ValueError("Invalid local memory.")
        return row[0], document

    def write(self, document, revision):
        encoded = json.dumps(document, ensure_ascii=False, sort_keys=True)
        if len(encoded.encode("utf-8")) > MAX_PROFILE_BYTES + 20000:
            raise ValueError("Local memory is too large.")
        with self.connect() as connection:
            if revision == 0:
                cursor = connection.execute("INSERT OR IGNORE INTO current_memory(id,revision,document) VALUES(1,1,?)",
                                            (encoded,))
            else:
                cursor = connection.execute("UPDATE current_memory SET document=?,revision=revision+1 "
                                            "WHERE id=1 AND revision=?", (encoded, revision))
            if cursor.rowcount != 1:
                raise MemoryConflict("A newer local memory was saved in another session.")
        return revision + 1
