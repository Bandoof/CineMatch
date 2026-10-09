# Changelog

Changes are recorded by engineering milestone; these headings are not published tags.

## Unreleased — v1.1 engineering work

- Contributor/security policies, architecture and development documentation.
- Python and Actions dependency update proposals; Python CodeQL workflow.
- Linux/Windows test matrix and measured coverage reporting without a forced threshold.
- Pinned action revisions, read-only default workflow permissions and PR/issue templates.

- Extracted typed profile state transitions; strict incremental Mypy and local hooks.
- Hardened corrupt autosave JSON handling and added transactional/isolation regressions.

## 2026-10-09 — review and security fixes (PR #1)

- Retry Wikipedia soft errors and clear stale metadata when source identity changes.
- Snapshot rating edits/deletions and watched restoration for ML Lab comparison.
- Reject ambiguous JSON/non-finite constants, malformed or untrusted source URLs.
- Update Streamlit/Pillow; dependency audit CI; safer local server/container defaults.
- 77 synthetic tests passed; see the dated security review for verification scope.

## Earlier design and ML v3 milestone

- Bilingual recognition, watchlist/watched history, feedback scopes and autosave.
- Independent MovieLens 1M benchmark: Adaptive +13.3% relative NDCG@10 versus
  popularity for three initial ratings only; no improvement at five/ten.
- See the [model card](docs/ml-v3-model-card.md) and historical verification reports.
