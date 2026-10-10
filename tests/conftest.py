import numpy as np
import pandas as pd
import pytest

from src.data import GENRES


@pytest.fixture
def sample():
    movies = pd.DataFrame({"movie_id": range(1, 13),
                           "title": [f"Test film {i} (1995)" for i in range(1, 13)],
                           "year": [1995] * 12,
                           "genres": [("Action", "Sci-Fi")] * 6 + [("Drama", "Romance")] * 6})
    for genre in GENRES:
        movies[genre] = movies.genres.map(lambda values: int(genre in values))
    rng = np.random.default_rng(42)
    rows = []
    for uid in range(1, 13):
        for mid in range(1, 13):
            if rng.random() < .85:
                liked = (uid <= 6) == (mid <= 6)
                rows.append((uid, mid, 5 if liked else 1, len(rows) + 1))
    ratings = pd.DataFrame(rows, columns=["user_id", "movie_id", "rating", "timestamp"])
    return movies, ratings


@pytest.fixture
def dataset_dir(sample, tmp_path):
    movies, ratings = sample
    ratings.to_csv(tmp_path / "u.data", sep="\t", header=False, index=False)
    lines = []
    for row in movies.itertuples():
        fields = [row.movie_id, row.title, "01-Jan-1995", "", ""]
        fields += [int(g in row.genres) for g in GENRES]
        lines.append("|".join(map(str, fields)))
    (tmp_path / "u.item").write_text("\n".join(lines), encoding="latin-1")
    return tmp_path
@pytest.fixture(autouse=True)
def isolate_service_mode(tmp_path, monkeypatch):
    # Existing UI regressions exercise the explicitly supported classic surface.
    # Product UI tests override this to exercise the new default entry point.
    monkeypatch.setenv("CINEMATCH_UI", "classic")
    monkeypatch.setenv("CINEMATCH_MAINTENANCE", "0")
    monkeypatch.setenv("CINEMATCH_MAINTENANCE_FILE", str(tmp_path / "maintenance.flag"))
