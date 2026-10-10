# CineMatch v1.2 experimental model card

**Status (2026-10-10): infrastructure recovered; selected model and final quality
unverified. No new production policy or trained model is released.** See
[research recovery](ml-v12-research.md), [protocol](ml-v12-evaluation.md) and
[machine-readable status](../reports/ml_v12.json).

## Intended use and artifacts

Offline MovieLens new-user movie ranking on CPU, using explicit-rating ALS,
title/genre TF-IDF/LSA and optional multilingual MiniLM with validation-selected
blends. Movie/series app ranking retains its existing policy. PR #14 explains
actual contributions and feedback/variety heuristics; these are attribution,
not causal explanations or enjoyment probabilities. Recovery adds evidence
verification and reports, not runtime ranking changes.

The failed session reported 32 ALS factors, bias regularization 20, fold-in 1 and
user-centered TF-IDF. These are **reported selections**, not recovered trained
artifacts. Regularization, calibration, blend weights, validation margins and
frozen source/selection hashes are missing. Do not build a production model from
the statement. The search config specifies 15 epochs and random state 42, but
the unavailable run's compliance cannot be independently established.

The optional encoder's revision/weight/tokenizer hashes are pinned in source and
config. ONNX quint8 AVX2 uses CPUExecutionProvider and one thread, with explicit
verified downloads outside Git. Lexical models and app need no optional encoder
dependencies. Real CPU integration tests passed during recovery; Windows latency
and Ukrainian interaction-quality claims do not follow from those tests.

## Evaluation, uncertainty and risks

The manifest contains 171 validation and 326 test users mutually disjoint and
outside 701 historical targets. Input hashes and 11 historical file hashes match
the [integrity receipt](../reports/ml_v12_integrity.json). Temporal/cohort/candidate
guards and selection/final paths are exercised by synthetic tests.

Reported three-rating NDCG@10 is 0.0987 Adaptive versus 0.0838 Popularity (+17.8%),
with paired absolute-difference interval [+0.0017, +0.0276]. **Experimental values
and interval are unverified.** Ten-rating means/interval endpoints and coverage/
diversity/novelty magnitudes are missing. MiniLM's alleged rejection lacks saved
trial evidence. No independently verified v1.2 quality, significance, fairness
or runtime-cost result is available.

- Historical explicit ratings and future-positive eligibility favor active raters
  and do not represent all visitors or current catalogs.
- Archive metadata lacks private v3 descriptions and as-of-rating guarantees;
  pretrained weights postdate the historical interactions.
- Coverage/diversity/novelty need original recommendation evidence. Offline ranking
  does not establish satisfaction, series quality or live onboarding gains.
- Historical v3 validation/test overlap is 199 users, and its inspected outcomes
  are development evidence.
- The final cohort was reportedly viewed. Treat it as consumed; reruns are
  replications and cannot guide new tuning.

No private profiles/SQLite are accessed, no data/weights committed, no paid APIs
added, no PRs merged and no app deployed. Model promotion needs original frozen
artifacts or newly separated evaluation followed by owner review. Regression
tests support their fixtures, not all hardware or recommendation quality.
