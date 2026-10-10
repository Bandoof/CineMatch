# Changelog

Changes are recorded by engineering milestone; these headings are not published tags.

## Unreleased — v1.3 Modern Movie Discovery

- Separate validated TVmaze/optional TMDB catalog, stable namespaces and explicit
  identity provenance; bounded API caches, offline snapshots and provider attribution.
- Indexed Ukrainian/English/original title search, typos, transliteration, mixed
  queries, remake disambiguation, filters and stable sorts.
- Dark native consumer navigation, responsive bounded poster cards, actual title
  details and clearly defined discovery shelves. One page renders per rerun.
- Existing ML algorithms/weights remain fixed; modern cold titles use disclosed
  genre/source-quality ranking. Research controls remain accessible separately.
- Reversible library actions, autosave/CAS, named/JSON profiles and atomic optional
  schema-6 identity restoration; schemas 2–5 remain compatible.
- Real desktop/mobile Chromium QA, reproducible synthetic measurements and bilingual
  setup/limits. No merge, tag, Release, deployment or new real holdout was performed.
- Historical +17.8% remains unverified and all surviving research bytes preserved.
- See [v1.3 verification and review order](docs/release-v13.md).

## Unreleased — v1.2 engineering and research infrastructure

- Reproducible offline research with pinned data, disjoint cohorts, validation-only
  selection and frozen-source/final-access safeguards.
- Controlled ALS and content experiments; optional multilingual MiniLM on CPU.
- Faithful Ukrainian/English score explanations without changing production defaults.
- Research regression tests, read-only evidence verification and exact evidence bytes
  on Linux/Windows.
- Interrupted experiment documentation: reported +17.8% NDCG@10 gain remains
  **unverified**; missing final results are not reconstructed or advertised.
- See [release preparation](docs/release-v12.md) for verification and research limits.

## v1.1 engineering milestone

- Contributor/security policies, architecture and development documentation.
- Python and Actions dependency update proposals; Python CodeQL workflow.
- Linux/Windows test matrix and measured coverage reporting without a forced threshold.
- Pinned action revisions, read-only default workflow permissions and PR/issue templates.

- Extracted typed profile state transitions; strict incremental Mypy and local hooks.
- Hardened corrupt autosave JSON handling and added transactional/isolation regressions.

- Reuse explanation context per list and MMR feature slice; preserve exact synthetic outputs.
- Skip unused literal-search title work; add bilingual watched-search and artifact-recovery regressions.
- Upgrade checkout/setup-python to pinned v6 revisions after CI Node20 warnings.
- Reproducible offline performance harness and before/after measurements.

## 2026-10-09 — review and security fixes (PR #1)

- Retry Wikipedia soft errors and clear stale metadata when source identity changes.
- Snapshot rating edits/deletions and watched restoration for ML Lab comparison.
- Reject ambiguous JSON/non-finite constants, malformed or untrusted source URLs.
- Update Streamlit/Pillow; dependency audit CI; safer local server/container defaults.
- 77 synthetic tests passed; see the dated security review for verification scope.

## Earlier design and ML v3 milestone

- Bilingual recognition, watchlist/watched history, feedback scopes and autosave.
- Historical MovieLens 1M benchmark recorded Adaptive +13.3% relative NDCG@10 versus
  popularity for three initial ratings only; no improvement at five/ten. Its
  validation/test targets overlap; inspected outcomes are development evidence for v1.2.
- See the [model card](docs/ml-v3-model-card.md) and historical verification reports.
