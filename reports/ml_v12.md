# v1.2 recovery result — 2026-10-10

**No independently verified final v1.2 benchmark can be published from available
evidence.** Protocol and implementation survived; validation, frozen selection
and final outputs were not found in accessible Git branches, local files or
GitHub Actions artifacts.

| Item | Verified result |
| --- | --- |
| Validation/test users in saved manifest | 171 / 326 |
| Mutual overlap/historical target reuse | 0 / 0 |
| Historical targets excluded | 701 |
| Config, public archive and input hashes | Match |
| Historical benchmark evidence | All 11 files unchanged |
| Selected model/final means/confidence intervals | Missing; unverified |
| Real final test scored during recovery | No |

The user quoted these outcomes from the failed session:

| Three seed ratings | Reported NDCG@10; unverified |
| --- | --- |
| Adaptive | 0.0987 |
| Popularity | 0.0838 |

Reported gain: +17.8%; paired absolute-difference 95% interval [+0.0017, +0.0276].
Rounded-mean arithmetic is consistent; it does not verify the experiment.
The ten-rating interval reportedly includes zero. Coverage reportedly rises,
genre diversity and novelty fall; values and rejected MiniLM scores are missing.
These are attributed statements, not results measured during recovery.

The quoted selection is ALS (32 factors, bias regularization 20, fold-in 1) and
user-centered TF-IDF; frozen regularization/calibration/blend evidence and trained
caches are absent. Treat the final cohort as consumed; never tune on it or
recreate a claim of a fresh unseen test.

[Research and reproduction](../docs/ml-v12-research.md) ·
[Model card](../docs/ml-v12-model-card.md) ·
[Machine-readable report](ml_v12.json) ·
[Integrity receipt](ml_v12_integrity.json) ·
[GitHub PR/check snapshot](ml_v12_recovery_github.json) ·
[Executed regression/security checks](ml_v12_recovery_checks.json)

Owner merge order: #12 → #13 → #14 → recovery follow-up. After each prerequisite
merges, retarget the next PR to `main` and refresh checks. Engineering work is
reviewable; verified model-quality integration is blocked on original final
artifacts. Production policy and private data are unchanged.
