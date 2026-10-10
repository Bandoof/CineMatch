# Verification — 8 October 2026

## Executed

- Windows Python 3.10.11: **22 tests passed**; Ruff passed.
- Linux Docker, Python 3.11: **22 tests passed**; Ruff passed. Current source was
  mounted read-only into the test image, with pytest cache writes disabled.
- The runtime Docker image built successfully, ran as the `cine` user, served
  Streamlit on a localhost-only test port, and passed its HTTP health check.
- Official MovieLens download/checksum, full canonical model training, EDA and
  protocol-2 evaluation ran successfully. All 100,000 source events remain;
  99,693 distinct canonical user/title pairs enter full-data model fitting.
- TVmaze downloaded a real 602-series metadata snapshot, with source URLs,
  attribution, optional poster links and a fetched date.
- Presentation metadata was downloaded via exact IMDb joins and Wikidata:
  854 Ukrainian film titles, 395 Ukrainian series titles, image links for 1,246
  films and posters for 602 series. Source IDs and original title/year remain
  stable; tests confirm model scores are identical after localization.
- Recognition-flow regressions cover rating, unwatched skips, exclusion from
  future prompts, undo, save/reload, old JSON compatibility and no conversion of
  skips into dislikes. Wrong remake mappings and untrusted image URLs are rejected.
- Real browser verification covered the Ukrainian default, demo ratings for both
  films and series, the series-only filter and personalised explanations, model
  lab tables, bootstrap intervals, model comparison and language switching.
  Screenshots and the GIF are actual app captures.
- Browser verification of the redesign covered Ukrainian Star Wars with its
  real poster, a 5-star rating advancing to Breaking Bad / Пуститися берега,
  "Не дивився" advancing to Toy Story / Історія іграшок without increasing the
  rating count, and language switching with the same stored ratings.
- The EDA notebook's code cells were executed when creating the source archive.
  Archive contents were checked for integrity and exclusion of raw data, models,
  profile storage, caches and Git internals.

## Review fixes

The original review's two P2 issues are resolved:

1. Duplicate identities now have canonical IDs and preserved aliases. Rated and
   hidden aliases exclude the whole identity. Earlier rating events remain available
   before future updates; regression tests cover those boundaries.
2. Engine cache signatures include input data, series, model and report artifacts.
   Creating or updating a report invalidates the cache without changing the data.
   Missing, stale and incomplete report artifacts have explicit fallbacks.

## Limits

### Watchlist, watched history and recovery — 9 October 2026

Windows / Python 3.10: **33 tests passed**, Ruff passed. New cases cover watchlist
actions from recognition and recommendations, unscored watched exclusions,
optional ratings, cancellation/undo, schema-4 JSON and local persistence,
legacy imports, canonical aliases and SQLite transaction cleanup. A series-only
profile personalizes Hybrid film ranking even at the validated alpha of 1.0;
film-rated profiles retain the original benchmark formula.

Fault injection verifies that import/runtime failures display neutral messages
in Ukrainian and English without traceback/private path leakage. Planned
maintenance skips application/model loading and the retry action sees its switch
change. The browser displayed the maintenance announcement during the update;
the normal site was restored after restarting the independent background server.
Browser verification added Star Wars from recognition and Breaking Bad from
recommendations to the same watchlist, then marked Breaking Bad watched without
a rating. The optional feedback panel appeared and its card was replaced in the
recommendations. Screenshots show the actual Ukrainian interface and posters.

The new Linux run could not start because Docker Engine was unavailable. The
earlier 22-test Linux result above applies to the prior version. No new ML
evaluation or remote workflow run is claimed for these changes.

### Local startup repair — 9 October 2026

The app was unavailable because no process was listening on localhost:8501.
The Windows launcher now starts Streamlit independently of its console, waits
for a successful health response and opens the page. Startup logs and the child
PID are recorded under the ignored `data/runtime/` directory. A second launch
reused the same PID; the server remained available after the launcher exited.
Ruff passed for the launcher. The existing browser tab displayed the full
Ukrainian interface and real poster after recovery.

GitHub Actions is configured for Python 3.10/3.11, but no remote workflow run or
GitHub publication is claimed. Docker downloads were not rerun inside the container;
the runtime verification mounted the already checked local dataset and numeric model.
Bootstrap/onboarding results measure historical MovieLens films, not series quality.


## Expanded films and not-interested feedback — 9 October 2026

Windows / Python 3.10: **41 tests passed**, Ruff passed. The expanded engine loaded
without warnings with 10,123 films / 602 series, 6,111 translated film names,
395 translated series names and image links for 9,395 films. All four requested
films have verified names and image URLs; Léon retains original catalog ID 55.
Old profile IDs/aliases, isolated dataset users, half-star ratings, literal/accent
search, remake boundaries, sparse-versus-dense KNN equivalence, bounded storage,
mixed-type quotas, reversible genre discount and scoring cache isolation are tested.

The independent expanded tuning/evaluation used the official pinned latest-small
archive, 200,836 real events, a global time split and validation-only parameter
selection. The full-data model is separate from evaluation models. Recall and
precision improved as point estimates while NDCG and coverage decreased;
the 28-user paired NDCG interval includes zero. No universal accuracy win is claimed.
The sparse KNN persistent matrices occupy 4,825,104 bytes. Missing/incompatible
model reconstruction follows the valid report's selected training parameters.

The runtime server was restarted independently and maintenance was disabled.
New Linux, remote CI and GitHub publishing were not run or claimed.

## Automatic memory and Docker — 9 October 2026

Windows / Python 3.10: **46 tests passed** in 22.52 seconds; Ruff passed.
Linux / Docker / Python 3.11: **46 tests passed** in 10.35 seconds; Ruff passed.
The test image was built from the current code. Runs used `--network none` and
no host/private-data mounts. Docker Desktop is available. No remote CI run is claimed.

New tests verify restoration of ratings, watched, watch-later, Not interested,
recognition skips and language in a fresh session; clearing; disabling/re-enabling;
demo and named-profile isolation; optimistic concurrency conflicts; damaged
snapshots, unavailable storage and hosted-mode disablement. Local storage never
replaces named copies implicitly or silently overwrites a newer snapshot.

In the real in-app browser, Interstellar was added to Watch later, the page
was reloaded, and the same title/list count was restored. The temporary test
entry was removed afterward. The Not interested caption and Undo action were
visually checked and that temporary mark was also undone. Search found all four
requested titles, including literal 1+1 and Leon/Léon.


## Content learning, Adaptive and redesigned UI — 9 October 2026

Final Windows / Python 3.10 run: **61 passed** in 31.80 seconds.
Final Linux / Docker / Python 3.11 run: **61 passed** in 15.34 seconds.
Ruff passed on both platforms. The 15 warnings are dependency deprecations.
The Docker image contains the final seed-scenario radio controls and regression
tests; it was run without network or host/private-data mounts. PyArrow is pinned
to 25.0.1 for NumPy 1.26 compatibility; an unpinned newer version broke tables.

Tests cover source/identity guards, vocabulary fitting on background items,
signed text preferences, policy validation, title-only/topic/session exclusions,
profile version 5 imports and undo, exploratory recognition, current and archived
ML Lab tabs, and actual displayed metric changes for 3/5/10 seeds. Browser QA
caught and fixed a nested-expander error and a noncommitted slider interaction.

The real browser showed the new Ukrainian guide with all rating/watchlist controls,
source posters, topic search, title-only exclusion, Undo and before/after lists.
A temporary watchlist entry survived reload and was removed. Temporary dismissals
were undone; the user's ongoing ratings and library updates were preserved.
ML Lab was checked against recorded data: the 3-seed Adaptive NDCG is 0.07439285,
Popularity 0.06566868, paired difference +0.00872417 with interval
[+0.00305867, +0.01438752]. Switching scenarios changes the actual table.
Native screenshots are in assets/cinematch-v3-guide.png and
assets/cinematch-v3-before-after.png. No viewport override was used.

Independent MovieLens 1M run: 1,000,209 events, 300 validation targets and 600
test targets; mixtures selected only on validation. The 3-seed relative NDCG gain
is 13.3%; 5/10 policies equal Popularity. Current descriptions are retrospective;
this is not an app/series accuracy result. See reports/ml_v3.md and the model card.
The exact public content snapshot is packaged separately with its checksum and
source attribution. Source archives exclude datasets, models, local profiles and
secrets. Remote CI and a cloud task are separate from these local checks.
# GitHub publication verification — 2026-10-09

Published the reviewed source to https://github.com/Bandoof/CineMatch.
Commit b64c7b12c97ac158e23947598bd2c1792b49f95f contains 101 files,
including all 17 owner-approved illustrations. All remote blob hashes match
the reviewed local file bytes. Data, models, secrets and personal profiles
are excluded. The original local app and private database remain on the PC.

Hosted run https://github.com/Bandoof/CineMatch/actions/runs/37924477380
(source commit 25b982a40d97e7468c1a8b5b830a294f9ddbebde) completed
successfully: both Python 3.10 and 3.11 jobs passed Ruff and pytest.
This confirms hosted checks separately from the historical local records below.

## v1.2 recovery verification — 2026-10-10

The combined #12/#13/#14 code and recovery verifier passed **159 tests, zero
skipped**, including both pinned-weight real MiniLM CPU tests and six new
evidence-corruption/read-only tests, on Python 3.11.16. Coverage was 73%; 14
warnings were existing Matplotlib/Pyparsing deprecations. Ruff, configured Mypy
(three modules), pre-commit including new files, pip check and exact integrity
receipt reproduction passed. Tests cover movie/series ranking, old/current JSON
profiles, SQLite rollback/autosave, watched/watchlist, negative feedback, Undo,
UK/EN rendering, optional-dependency fallback and numerical artifact recovery.
Fixtures use temporary data; no private database was opened or rewritten.

The `requirements-research.txt` audit found no known vulnerabilities. The broader
installed-environment audit initially reported 14 advisory entries in bootstrap
pip 24.0/setuptools 79.0.1. Updating only this virtualenv to pip 26.2.1/setuptools
83.0.0 made that audit pass with no known vulnerabilities. Repository dependency
pins were unchanged. Full executed-check details are saved in
[the QA receipt](../reports/ml_v12_recovery_checks.json).

Existing PR heads had successful Ubuntu Python 3.10/3.11, Windows Python 3.11,
security and CodeQL checks, verified via GitHub API and saved with exact SHAs in
[the GitHub receipt](../reports/ml_v12_recovery_github.json). CodeQL was not run
locally. Current follow-up checks must be read on its PR; historical success is
not a guarantee for later commits. Ancestry and three `git merge-tree` operations
confirmed the stack combines without conflicts at those heads.

The initial follow-up Windows job caught Git newline conversion changing
`reports/performance_v11.json`. Git attributes now preserve exact committed bytes
for report/config evidence and Python source, retaining original CRLF/LF files
without changing historical artifacts. A checkout with `core.autocrlf=true` and
new hosted Windows checks validated the repair. The repair commit
`828bfe75c4fc650985d6240f07cb02c26253489e` passed Ubuntu Python 3.10/3.11,
Windows Python 3.11, security and CodeQL; exact check URLs are in the QA receipt.

A later Windows pull-request run exposed the guided Undo UI test's default
three-second AppTest rerun timeout; the push run on the identical commit passed.
Discovery and basic app tests now use the same bounded 30-second default as
other UI tests, including widget reruns. All state assertions remain, and runtime
latency is still measured by the separate performance tests.

The real final test cohort was not evaluated. Original selection, validation and
final metric files are missing. The quoted +17.8% gain and interval remain
unverified; neither passing tests nor the saved manifest establishes them. See
[research recovery](ml-v12-research.md) and [model card](ml-v12-model-card.md).
