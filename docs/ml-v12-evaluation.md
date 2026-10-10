# v1.2 evaluation protocol — frozen 2026-10-09

Research branch, not an application-policy upgrade. The numerical search space is
fixed in [the versioned configuration](../configs/ml-v12-2026-10-09.json) before
new model outcomes. Existing `ml_v3` evidence is immutable. v3 had 199 overlapping
target users across different temporal boundaries: their future test ratings did
not enter validation training, but validation and test are not independent user
samples. Repeated users can make tuning more tailored to the tested population;
user bootstrap intervals do not capture this model-selection dependence.

## Data and cohorts

GroupLens MovieLens 1M, official pinned ZIP SHA-256
`a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`.
Respect the archive's research-only/commercial-permission and non-redistribution
terms. No demographics, private database, profiles or app-trained artifacts are
used. Downloaded files and weights stay outside Git.

Global 80/10/10 timestamp groups preserve ties: train ends at 975768738, validation
at 978133367. Users must have >=20 distinct pre-boundary ratings and an unseen
future rating >=4. Eligibility therefore conditions on observed future ratings;
results are not representative of visitors who never rate or never like anything.

Exclude the union of 701 v3 target IDs. Select up to 200 validation users by a
fixed SHA-256 ID order. Select up to 400 test users by the same predefined order,
excluding validation IDs too. Before either fit, exclude the entire histories of
**both** reserved cohorts. Validation uses train only; final uses train+validation
only. Test ratings only supply eligibility and labels, never statistics/features.
This preserves a previously unused target-user holdout within this experiment;
it is not a new dataset or externally untouched research population. Historical
v3 test observations motivated the research questions and are development evidence.

## Candidates and measurements

Matched users for 1/3/5/10/20 seeds. Primary profiles use the most recent distinct
pre-boundary ratings, stable `(timestamp, canonical movie ID)` ties. Every method
ranks the full canonical catalog minus supplied seeds with ID-based score ties.
No negative sampling. All past-seen titles are excluded from positive labels;
unavailable future positives remain in recall/NDCG denominators. Previously seen
non-seed titles may consume slots. A separately labelled full-history-filter
diagnostic measures that cost; it is not compared as the same cold-start task.

Macro Precision/Recall/NDCG@10; full-catalog coverage; mean pairwise genre cosine
distance; novelty `-log2((background_count+1)/(total_count+catalog_size))`.
Novelty/diversity are descriptive tradeoffs, not satisfaction or accuracy. Record
training/load time, warm scoring/ranking latency, numerical artifact size and
peak process RSS. Hardware results describe this cloud CPU, not a Windows PC/GPU.

2,000 paired user bootstrap samples, seed 20261009, identical draws across models.
Report metric intervals and paired NDCG differences from Popularity. These are
pointwise intervals conditional on selected configuration, users and dataset;
they do not correct multiple comparisons or capture deployment/parameter shift.
Prespecified primary outcome: validation-selected composite vs Popularity at
three seeds. Other seed lengths/ablations are secondary, not independent winners.

## Selection and final access

Validation chooses a single collaborative configuration by mean NDCG across seed
counts; a single semantic/preference variant likewise; then seed-specific
nonnegative mixtures and fixed-vs-percentile calibration by validation NDCG.
The broader search increases selection uncertainty. All validation trials remain
visible. Freeze source/input/config/selection hashes before final evaluation.
The final CLI refuses changed inputs/code and reserves an exclusive test-access
marker before scoring; it never overwrites evidence. A fresh reproduction after
seeing results is a replication, not a new untouched test. Do not retune on it.

The primary experiment uses **archive titles and genres only**. The owner's v3
Wikipedia/TVmaze description snapshot is unavailable here; exact v3 semantic
reproduction is impossible. Title/genre LSA is labelled separately. Pretrained
multilingual weights postdate these historical interactions; neural results are
retrospective representation tests, not historically deployable predictions.

Onboarding simulations reveal only real pre-boundary ratings when a prompted
title exists in a user's history. Missing titles are skips, never synthetic
negatives. Compare strategies on the same users and labels; report prompt cost
and availability. This oracle of rated-title familiarity is biased and not a
live active-learning experiment. Series, dismissal actions and live satisfaction
have no interaction-quality evidence in MovieLens and remain outside the scope.
