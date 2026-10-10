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

- [x] Credential-free dated real film/series metadata; traceable legitimate UK
  labels, namespaces/dedup tests, bounded explicit refresh; no invented ratings.
- [x] Correct provider error feedback, useful empty/offline states and preserved
  bilingual selections; no misleading saved-success messages.
- [x] Labeled synthetic demo profile with positive/negative ratings, watched and
  watchlist; independent visitor state, reset, no local private storage access.
- [x] Desktop/mobile/tablet browser journeys, independent contexts, reset/refresh,
  controlled offline/errors, basic accessibility checks with manual gaps disclosed.
- [x] Same benchmark fixtures/output hash; resource/session and Docker checks.
- [x] Bilingual portfolio README/case study/architecture, real screenshots,
  3–5 minute scripts/storyboard/subtitles and hosting/threat-model documentation.
- [x] All tests/security/evidence checks pass; focused v1.4 PRs pushed, unmerged.

No public deployment, tag, GitHub Release, private infrastructure modification or
v1.4 merge is authorized. Recovery: fetch/read current GitHub PR state; resume the
first unchecked item. Never repeat completed v1.3 merges or research holdouts.

Product/catalog checkpoint: 30 real titles (22 films / 8 series), 30 source UK
labels, 25 UK short descriptions, 8 poster URLs / attributed community ratings.
19 titles have source release years >=2023; 5 precise dates within 730 days.
9 ambiguous/missing precise dates are withheld while source years remain useful.
Initial capture 14 live requests; label-priority refinement 4 live / 10 hits;
final reconstruction 0 live / 14 hits. TMDB credential absent; no live claim.
Wikidata/TVmaze data license is separate from code; no artwork bundled.

Demo checkpoint: dedicated `app/portfolio_app.py`, no SQLite/import/provider client
paths. Independent AppTest sessions, reset/Undo, fresh-session reset and original
formula cache equivalence passed. Optional public pack prepared from verified
official archives: 222 titles / 30,000 input events (29,974 canonical latest events),
248 combined identities. Seven recommendation modes exercised on the real pack.
Source files/DBs/models remain outside Git. No owner DB created.
PR #20: https://github.com/Bandoof/CineMatch/pull/20 (main base, unmerged).

QA checkpoint: PR #22 https://github.com/Bandoof/CineMatch/pull/22 (base #21).
233 local / 231 Docker + 2 optional skips; exact original score hash preserved.
Streamlit 1.54 native ARIA defects motivated 1.65; native form submissions tested
with batched input, without changing the expected rating. Real 18-flow browser
run and independent GitHub browser CI passed with 0 page errors/failed requests.
Seven axe views: no violations, one incomplete ARIA item needing manual review.
Invalid pack warning/fallback tested separately, no SQLite sentinel created.
Fresh Linux/Windows/security/CodeQL checks passed on 796c44f; the follow-up adds
research capture and settled-state synchronization, so fresh checks must finish
before review-ready status. Artwork-free shareable captures are in progress.
Recovery: finish the first remaining media/docs checkbox and inspect actual GitHub
heads. Main remains 40eb03f; do not merge v1.4 or deploy without owner approval.

Final shareable capture: 19 journeys including Research, all three viewports,
0 page errors / failed requests, posters disabled. Invalid-pack fallback also
passed independently. Real files are ready for the presentation PR; no narrated
3–5 minute video has been recorded. Only actual silent QA footage is available.

Delivery checkpoint: #20 → #21 → #22 → #23, all OPEN/unmerged, review-ready.
Last code head #22: 83437f9d8b5fc34a2f16a5a112fc32a7b4cff7f6; Linux/Windows,
audit/CodeQL and browser checks passed. Presentation head 0086d05 also passed
fresh checks. This documentation/evidence follow-up receives its own new CI.
Final clean-archive Docker suite: 231 passed / 0 failed / 2 skipped, network none.
An initial collection run hit ENOSPC (12 collection errors); unchanged tests passed
in isolated tmpfs /tmp and cache paths. No tests/trust stores were weakened.
13 screenshots / 24 draft caption cues / original reports+configs bytes verified.
Narrated video remains owner work. Actual 65.44-second silent QA MP4 is local-only:
/workspace/cinematch-v14/media/qa-walkthrough.mp4; no video was uploaded to GitHub.
Full Ukrainian report: docs/final-report-v14-uk.md. Capture hashes and scripts allow
recovery without this chat. No public hosting, new merge, tag or Release performed.
Recovery: read actual PR heads/checks; owner review before retargeting each lower
PR to main after the preceding approved merge. Do not rerun the consumed holdout.
