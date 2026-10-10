# Safe portfolio demonstration / Безпечна демонстрація

```bash
python -m streamlit run app/portfolio_app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

No download/key/account is needed for the shipped 30-title metadata demo. Its
profile is visibly **synthetic**, with positive/negative preferences, watched
titles and a watchlist. Title metadata is real. Reset restores the same example;
Start with an empty profile clears only this visitor. Page refresh creates a new
websocket session and restores the example. Language/poster preferences survive
the reset button within a session. Nothing is written to owner profiles.

For actual original ML recommendation modes, explicitly prepare a small public
development pack before running the same app:

```bash
OPENBLAS_NUM_THREADS=1 python -m scripts.prepare_portfolio --directory data/portfolio
```

PowerShell: `$env:OPENBLAS_NUM_THREADS="1"`; then run the Python command without
the Unix environment prefix. Set `CINEMATCH_PORTFOLIO_DATA_DIR` only to another
pack created by that script. Existing destinations are refused, never overwritten.
Both official GroupLens archive hashes are verified. Only at most 250 real titles
and 30,000 real development events enter the pack; the ordinary model defaults
are fitted into a **separate demo artifact**, not existing production weights.
Original numerical formulas/algorithms are reused. Duplicate canonical events
are collapsed by the existing engine. No real research holdout is run.
Retain GroupLens attribution/terms when preparing data; it is not redistributed
in Git. No public release of the pack has been authorized.

Without a valid prepared pack, For You explicitly shows genre/provider-quality
heuristics. With it, Known catalog / Adaptive is the original engine; modern
movies remain a separately disclosed heuristic. Neither is presented as a newly
verified scientific improvement. Research repeats the +17.8% unverified warning.

## Threat model and tested boundaries

Assets: owner profiles, provider credentials, another visitor's preferences,
server resources and scientific evidence. An anonymous visitor may change widgets,
query parameters and their own ratings repeatedly. Operator/host filesystem
compromise and malicious hosting administrators are outside this design.

- Dedicated entry point fixes the product surface and session demo flag, even if
  `CINEMATCH_UI=classic` or local autosave settings are present.
- No SQLite initialization/read/write, named profiles or profile import in demo.
  File export contains only that visitor's current synthetic/edited preferences.
- CatalogView, synthetic profile and optional Recommender are created separately
  for each Streamlit session. Provider clients and TMDB token reads are absent.
- No writable global visitor cache: the original score formula is bound to a
  **per-instance bounded LRU**, avoiding the original class-level profile-key LRU.
  Exact numerical equivalence is regression-tested. No shared `cache_resource`
  stores a demo Recommender/profile. The original local mode remains unchanged.
- Public pack reads use fixed filenames, provenance/hash/size/count checks and
  reject symlinked files. Ambient `CINEMATCH_DATA_DIR`, artifact paths and profile
  paths are ignored. Invalid packs leave a visible metadata-only fallback.
- No provider refresh or remote search buttons. Search text stays in the session.
  Optional TVmaze poster loads expose ordinary network information to the CDN;
  the notice explains this, and posters can be disabled for offline use.
- UI lists ≤12 cards; library/snooze/activity/cache state are bounded by catalog
  size/session caps. Session resets clear visitor score/index caches.

Two independent AppTest sessions verify changes, Undo and reset do not affect
each other; storage/client construction is patched to fail if called. Fresh
sessions restore only the example. Browser contexts and resource tests are
recorded in the final QA report. This is application-level session separation,
not a claim of complete host/network/security certification or DoS resistance.

Before any public deployment, the owner must review current hosting/provider
terms, resource/concurrency limits and privacy notice. Use the dedicated entry
point or Docker `--target portfolio`, omit secrets/private data, and do not expose
the local SQLite entry point. No public URL, deployment or account has been created.

Українською: стан кожного відвідувача окремий і тимчасовий. Демо не читає SQLite
або приватні профілі, не використовує токенів і не надсилає пошукових запитів
провайдерам. Звичайний локальний режим з autosave збережено. Без підготовленого
публічного ML-набору рекомендації чесно позначені як жанрові евристики; із ним
показано вихідний engine на обмеженому development-наборі, без нового holdout.
