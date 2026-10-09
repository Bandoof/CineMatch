# Architecture / Архітектура

CineMatch is a single local Python process with Streamlit sessions and SQLite.
It has no account service, external vector database or online training service.

| Layer | Responsibility | Dependencies |
|---|---|---|
| `app/streamlit_app.py` | Startup, maintenance and neutral failure page | Streamlit, interface |
| `app/interface.py`, `app/ml_lab.py` | Bilingual widgets and model comparison | Runtime, ranking service, interchange |
| `app/runtime.py` | Bounded engine cache, validated artifacts and fallbacks | Catalog/loaders, numerical models |
| `app/recommender.py` | Shared scoring, exclusions, mixed-media quotas, explanations | Pure numerical modules in `src/` |
| `src/collaborative.py`, `item_knn.py`, `semantic.py` | ALS, observed-rating KNN, TF-IDF/LSA | NumPy/SciPy/scikit-learn |
| `src/profile_actions.py` | UI-independent replace/rate/seen/cancel/Undo transitions | Mutable state mapping; no Streamlit or I/O |
| `src/profiles.py`, `src/memory.py`, `app/memory.py` | JSON interchange, named profiles, autosave bridge | Local SQLite, UI state |
| `scripts/` | Explicit download, train, evaluate and maintenance commands | Official data sources and local artifacts |

Data is downloaded explicitly into ignored `data/`. Catalog canonicalization keeps
old IDs as aliases; film IDs are positive and TVmaze series IDs negative. Chronological
evaluation partitions events before fitting; the running app's full-data model is
not used to report test quality. Models are numerical NPZ files with fingerprints.
Metadata joins require verified source identity; display language does not change scores.

A UI action updates session state; `main()` saves in `finally`, including rerun actions.
Demo state is deliberately excluded from autosave. SQLite revisions reject stale writes
from a second session. JSON supports legacy mappings and schemas 2–5; import validates
before replacing current state. Watchlist, unwatched skips, watched history and
negative-topic feedback have different meanings and must remain separate.

Runtime cache keys include file path, modification time and size for catalogs/models/
reports/metadata. Engine entries are bounded to three; score-component entries to eight.
Returned score arrays are copied so UI/evaluation callers cannot mutate the cache.
This is reuse of trusted local artifacts, not a cross-user profile store. Corrupt models
can be rebuilt; missing metadata or series use explicit fallbacks.

Series lack MovieLens-style individual interactions and use disclosed content/quality
fallbacks. The independent benchmark concerns films, not series or live satisfaction.

Українською: UI, ранжування та локальне збереження — окремі шари. Зміни стану
зберігаються перед rerun; демонстраційні оцінки не замінюють пам'ять власника.
Опис моделі та обмеження: [model card](ml-v3-model-card.md).
