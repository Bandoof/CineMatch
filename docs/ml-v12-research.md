# CineMatch v1.2 research recovery — 2026-10-10

The implementation survived in PRs [#12](https://github.com/Bandoof/CineMatch/pull/12),
[#13](https://github.com/Bandoof/CineMatch/pull/13) and
[#14](https://github.com/Bandoof/CineMatch/pull/14). All were open and unmerged
when inspected. Exact commits, changed files and successful Tests, security and
CodeQL checks are saved in [the GitHub snapshot](../reports/ml_v12_recovery_github.json).

**The final ML improvement is unverified.** Attributed statements from the failed
session are preserved in [the recovery JSON](../reports/ml_v12.json), separate from
verified results, which are `null`. Recovery does not select parameters, fit models
or score the real final cohort. This document reconstructs an evidence audit, not
the lost numerical experiment report.

## Surviving evidence

| Evidence | Recovery finding |
| --- | --- |
| Frozen search config | Saved; matches manifest config and canonical SHA-256 |
| Dataset/cohort manifest | Saved; 171 validation and 326 test IDs, mutually disjoint and outside 701 historical targets |
| MovieLens inputs | Official archive downloaded separately; archive and three input hashes match |
| Historical benchmark files | All 11 hashes match baseline; no historical files replaced |
| Research runner | Saved; synthetic selection/final pipeline and exclusive-access regression tests pass |
| MiniLM encoder | Saved; both real pinned-weight CPU integration tests pass in recovery |
| Faithful explanations | Saved; bilingual attribution and movie/series fallback tests |
| `validation.json`, `selection.json` | Not found; selected models and trial comparisons cannot be established |
| `final-access.json`, `final.json`, `final.csv`, `per-user-metrics.csv` | Not found; means and intervals cannot be reconstructed |
| Original model/vector caches, logs and performance measurements | Not found; new downloaded weights are inputs, not recovered trained artifacts |

Search covered all current remote branch heads and their reachable history, local
reflogs/unreachable objects, workspace and `/tmp` experiment filenames, and GitHub
Actions artifacts, releases and tags. No unreachable local objects, Actions
artifacts, releases or tags were found. Files created by recovery pytest are
synthetic fixtures and excluded from evidence. The lost chat's runtime/transcript
is unavailable. This search cannot exclude copies elsewhere; the user-supplied
recovery request is the only available source for the final outcome statements.

## Verified protocol and search space

See [original methodology](ml-v12-evaluation.md) and
[integrity receipt](../reports/ml_v12_integrity.json). The receipt verifies saved
IDs/counts and bytes; it does not repeat future-label eligibility calculations
or prove that an unavailable run executed the protocol correctly.

The manifest records MovieLens 1M: 1,000,209 events, 6,040 users and 3,883 catalog
entries. Global 80/10/10 temporal groups preserve timestamp ties; train cutoff is
975768738, validation cutoff 978133367. Eligibility requires at least 20 distinct
past ratings and an unseen future positive of at least four stars. Fixed hash
ordering excludes historical v3 targets. Both reserved cohorts' entire histories
are removed from background training. Validation uses train only; frozen final
training uses train plus validation.

The config specifies ALS factors 16/32/64, regularization 3/10/30, bias strength 5
and additional bias trials 1/20 at factors 32 and regularization 10; 15 epochs,
random state 42. Fold-in trials are 1/10/30, history-scaled and the implementation's
training strength. Content uses TF-IDF, 64-dimensional LSA and optional MiniLM,
with signed, positive-only and user-centered preferences. CF/content selection
uses mean validation NDCG over 1/3/5/10/20 ratings; seed-specific blends use a
66-point nonnegative grid and fixed/percentile calibration.

Every method ranks the same full catalog with deterministic ID ties, no sampled
negatives, and supplied seed ratings excluded. Positive labels exclude all past
items; unavailable positives remain in denominators. Full-history filtering is
a separately labelled diagnostic. The prespecified primary comparison is selected
Adaptive versus Popularity after three ratings. Other counts, ablations and
onboarding simulations are secondary; simulation reveals actual past ratings,
and missing feedback is a skip rather than a synthetic dislike.

## Reported outcome; numerical evidence missing

| Three-rating outcome | Failed-session statement | Independently verified? |
| --- | --- | --- |
| Adaptive NDCG@10 | 0.0987 | No |
| Popularity NDCG@10 | 0.0838 | No |
| Relative improvement | +17.8% | Arithmetic matches rounded means; experiment unverified |
| Paired absolute-difference 95% CI | [+0.0017, +0.0276] | No |

Rounded means imply an absolute difference of 0.0149 and about 17.78% relative
improvement. Arithmetic consistency is not experimental verification. These
values must not enter the app benchmark display or be marketed as measured gains.
The ten-rating interval reportedly includes zero; endpoints and means are absent.

Planned uncertainty is a paired user percentile bootstrap with 2,000 common draws,
seed 20261009. Original ordered per-user precision/recall/NDCG rows would permit
recomputation without recommending anything again. If verified, a positive interval
would support the primary difference conditional on this configuration and sample;
it would not prove universal benefit, give a p-value, correct all comparisons or
capture selection/dataset uncertainty. A zero-crossing interval is inconclusive.

## Selected/rejected models and tradeoffs

The quoted selection is ALS with 32 factors, bias regularization 20, fold-in 1,
plus user-centered TF-IDF. It fits the search space. The code's bias-20 trial uses
regularization 10, but this is not verified selection evidence. Calibration and
per-seed blend weights are unknown. No model is rebuilt or promoted from guesses.

MiniLM reportedly was investigated and lost validation selection. **Actual scores,
selection margin and empirical rejection reason are missing.** Lexical/neural
inputs use the same archive titles/genres, with zero description coverage. This
does not establish inferiority for rich summaries or Ukrainian search. The pinned
model is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revision
`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, ONNX quint8 AVX2 on CPU. Recovery tests
establish finite normalized reproducible vectors, corpus parity and offline cache
reload, not interaction quality. Larger ALS, LSA, alternative fold-in/preference/
calibration/blend/onboarding trials are implemented, but their run status and
rejection reasons cannot be recovered.

Coverage reportedly increased while genre diversity and novelty decreased; no
magnitudes are available. Coverage is union Top-10/catalog size, diversity is
mean pairwise genre cosine distance, and novelty is negative log2 smoothed
background frequency. These tradeoffs do not measure satisfaction. The runner's
per-user CSV stores ranking metrics but no recommendation lists; those rows alone
cannot recompute coverage/diversity/novelty. Original recommendation outputs or
a disclosed replication would be needed for that stronger verification.

## Holdout state and limitations

Final outcomes were reportedly viewed. Conservatively treat the recorded 326-user
cohort as **consumed**, despite the missing access marker. Never tune on the quoted
outcomes, delete an access marker, or label a rerun as a fresh holdout. Any new
selection needs a preregistered separated development/test protocol, preferably
external data. Finding original outputs permits an audit, not further tuning.

Biases include historical explicit-rating selection, active-user/future-positive
eligibility, one known dataset, incomplete seed profiles and metadata without
as-of-rating guarantees. Modern pretrained weights postdate the interactions.
Historical v3 validation/test overlap is 199 users; its inspected outcomes are
development evidence. The private v3 description snapshot is unavailable, preventing
exact semantic reproduction. MovieLens IDs are public research IDs, not private
app profiles. Dataset terms apply; weights/data are not redistributed here.
TV-series quality, weak dismissal quality, live onboarding and satisfaction remain
unbenchmarked. Numerical explanations are not causal or enjoyment probabilities.

## Reproduction without final evaluation

With ordinary development dependencies, no downloads are needed:

```bash
python -m scripts.verify_v12_evidence
python -m pytest -q tests/test_v12_evidence.py tests/test_research_protocol.py tests/test_research_runner.py
```

For public input byte verification in a separate directory:

```bash
python -m scripts.download_research --directory ../cinematch-public-inputs
python -m scripts.verify_v12_evidence --data-dir ../cinematch-public-inputs/ml-1m --archive ../cinematch-public-inputs/ml-1m.zip --output ../v12-integrity-replication.json
```

`--output` refuses an existing path. Identical inputs reproduce the saved receipt
exactly; interactions are only hashed. Optional CPU tests require
`requirements-research.txt`, downloader `--embeddings` and
`CINEMATCH_RESEARCH_MODEL_CACHE` pointing to `minilm`. PowerShell uses
`$env:CINEMATCH_RESEARCH_MODEL_CACHE = '...'`. No paid API, private data or deployment
is needed. In this managed proxy the explicit certifi context needed the runtime
CA bundle. Recovery selected it process-locally with TLS verification intact;
pinned research source stayed unchanged.

Git attributes disable newline conversion for report/config evidence and Python
source. Historical artifacts contain both original CRLF and LF files; their bytes
are preserved rather than normalized. Windows checkout therefore retains the
same evidence hashes and frozen-source fingerprints as Linux.

Recovery also sets the remaining discovery/basic-app AppTest instances to the
existing 30-second UI test budget. This prevents the observed three-second Undo
timeout on shared Windows runners while retaining every state assertion.

If original outputs become available, preserve bytes in a new directory. Verify
manifest/config/input/selection/source/vector hashes with the exact frozen source
checkout and reconcile validation selection with final embedded selection.
Recompute paired means/intervals from ordered matched per-user rows; compare
JSON/CSV and disclose missing recommendation evidence. Do not run `research_v12
final` as an artifact-recovery shortcut. Full numerical reproduction remains
blocked by missing frozen evidence.

## Owner integration

Recommended order: **#12 → #13 → #14 → [#15](https://github.com/Bandoof/CineMatch/pull/15)**. The follow-up starts
at #14; all prerequisites are its ancestors. Keep the existing stack before
merging. After each owner-approved prerequisite merge, retarget the next PR to
`main`, inspect its narrowed diff and refresh CI/CodeQL. Prefer merge commits to
preserve ancestry; squash/rebase merges require reconciling dependent branches.
Engineering integration is reviewable: local QA and the repair commit
passed Ubuntu/Windows/security/CodeQL. Check the current PR head before merging. A scientifically
verified v1.2 quality release is blocked on missing final evidence. No PR is
merged, no production policy changed, and no application publicly deployed.
