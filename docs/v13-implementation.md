# v1.3 architecture assessment and review plan

Baseline: verified latest `main` **36d90f15cb874c4f7dd435d1d17b96221da3b83d**.
The existing local Streamlit/SQLite architecture, seven algorithms, stable
MovieLens/TVmaze IDs, profile schema 2–5 import, Undo, autosave/CAS and v1.2
evidence checks are reusable. They need no new account service or training policy.

The baseline catalog is a downloaded historical development snapshot; modern
movie availability requires a separate metadata provider. Literal row-wise title
search misses typos/transliteration. The existing UI renders every tab and many
hidden controls on each rerun, making ordinary discovery feel like a research tool.

The consumer catalog facade keeps provider metadata, namespace mapping and
cold-title discovery separate from the original training engine. That engine's
scores and weights remain unchanged. Native Streamlit navigation will render one
page at a time; the classic UI remains an explicit compatibility option.

Review sequence (dependent branches; no automatic merges):

1. Catalog metadata, validated providers/caches, identity facade, runnable catalog
   explorer and contract tests.
2. Indexed bilingual/typo/transliteration search, filters and transparent discovery
   collections, connected to the explorer.
3. Cinematic consumer UI, title details, actions and compatible local persistence.
4. Personal discovery/library refinements, browser QA, engineering measurements,
   documentation and release preparation.

Baseline execution in this managed Linux environment: **159 tests passed**,
including two real optional CPU encoder tests; Ruff, configured Mypy, all
pre-commit hooks and requirements audit passed. The reproducible 1,500-item /
2,400-event synthetic engineering harness measured cold AppTest 298.8 ms, warm
rerun 46.4 ms and Adaptive/Hybrid recommendations 1.30/1.43 ms. These are fixture
measurements, not live Windows latency or recommendation-quality results.

Scientific scope stays unchanged: the historical **+17.8% claim is unverified**,
the 326-user final cohort is consumed, and no real holdout is rerun or promoted.
Historical reports/datasets are not rewritten. API credentials remain optional;
no public deployment, GitHub Release or automatic merge is part of this work.
