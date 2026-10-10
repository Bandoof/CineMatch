# CineMatch v1.4 — verified progress and recovery

## Stage A complete — 2026-10-10

| PR | Merge commit |
|---|---|
| #16 | `2adde7975b3e353a7dfc1a9445bbf19c00e96405` |
| #17 | `71594c7c5e34a56afdd4a54847d5638b8d3eef53` |
| #18 | `d64fb0e1d9ddd53fd5493bd2b55ccecf85679940` |
| #19 | `40eb03ff0b0d8ecdfad83d22db08eaf5e552db0d` |

Exact final main: `40eb03ff0b0d8ecdfad83d22db08eaf5e552db0d`.
Each dependent PR retargeted to main, updated with a merge from main, actual diff
reviewed, tested and merged only after all fresh head checks succeeded. Each
post-merge main passed Linux 3.10/3.11, Windows 3.11, audit and CodeQL.
Final main: local **220 passed / 0 failed / 0 skipped** with pinned optional CPU
encoder cache; each CI platform and clean Docker **218 / 0 / 2**. Ruff, configured
Mypy, pre-commit, 101-dependency requirements and 107-dependency installed audits
passed (0 known vulnerabilities). Real Chromium 153 / Playwright 1.63: 13 flows,
desktop/mobile, 0 page errors / failed requests. Docker health passed with no
network/published ports. A first Docker build copied stale host bytecode and had
5 AppTest source-inspection failures; a clean Git archive build resolved them
without code/test changes. v1.4 will exclude nested bytecode from build contexts.

Original seven algorithms/configs unchanged. Surviving research evidence hashes
intact; +17.8% remains unverified, 326-user final cohort consumed, no holdout rerun.
Provider docs independently re-read; scoped attribution review, not legal certification.
Private QA logs/snapshots outside Git: `/workspace/cinematch-v14/stage-a`.
Portable summarized evidence will be saved in `reports/engineering_v14.json`.

## Stage B acceptance checklist

- [ ] Credential-free dated real film/series metadata; traceable legitimate UK
  labels, namespaces/dedup tests, bounded explicit refresh; no invented ratings.
- [ ] Correct provider error feedback, useful empty/offline states and preserved
  bilingual selections; no misleading saved-success messages.
- [ ] Labeled synthetic demo profile with positive/negative ratings, watched and
  watchlist; independent visitor state, reset, no local private storage access.
- [ ] Desktop/mobile/tablet browser journeys, independent contexts, reset/refresh,
  controlled offline/errors, basic accessibility checks with manual gaps disclosed.
- [ ] Same benchmark fixtures/output hash; resource/session and Docker checks.
- [ ] Bilingual portfolio README/case study/architecture, real screenshots,
  3–5 minute scripts/storyboard/subtitles and hosting/threat-model documentation.
- [ ] All tests/security/evidence checks pass; focused v1.4 PRs pushed, unmerged.

No public deployment, tag, GitHub Release, private infrastructure modification or
v1.4 merge is authorized. Recovery: fetch/read current GitHub PR state; resume the
first unchecked item. Never repeat completed v1.3 merges or research holdouts.
