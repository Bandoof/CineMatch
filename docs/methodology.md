# Current and archived methodology

The current content/Adaptive model is described in [the v3 model card](ml-v3-model-card.md).
The sections below record earlier genre/ALS experiments; their numbers must not be compared across datasets.

# Recommendation and evaluation design — protocol 2

## Expanded application and development evaluation

The current application combines the original catalog below with MovieLens
latest-small: 10,123 films, 200,836 rating events from 1,553 separately namespaced
users. Old movie IDs remain canonical; new IDs are 1,000,000 + latest movieId.
Latest user IDs also add 1,000,000 and are never assumed to identify 100K users.
Exact title/alternate-name joins include release years; this repairs Léon without
creating a second copy of the old Professional ID. IMDb links identify public
translation/image records without changing model features.

`scripts.improve_movies` evaluates the pinned expanded snapshot separately:
160,668 / 20,084 / 20,084 global chronological events, timestamp ties intact.
64 configurations tune ALS factors/regularization and Hybrid genre/quality weights
on validation only. The default selected model is 32 factors, regularization 10,
15 epochs; Hybrid for film-rated profiles is 60% ALS + 40% Bayesian popularity.
Scores retain the existing [1,5] clipping/rescaling convention even though real
input ratings from latest-small include 0.5 stars. Series-only genre fallback remains.

The same 28-user test cohort compares the previous default architecture retrained
on the expanded data. More relevant Top-10 results accompany slightly lower NDCG
and coverage; the paired NDCG interval includes zero. Onboarding uses the selected
parameters and excludes the entire evaluation users' histories. App models train
on full observations only after evaluation. Latest-small is a development dataset,
not a stable shared research benchmark. The checksum and full protocol are in
`reports/expanded_metrics.json`; the original 100K evaluation below is archived.

Not-interested feedback is stored separately from star ratings, under the compatible
profile `blocked` field. It excludes the title and subtracts up to 20% of each
algorithm's score range according to cosine genre similarity with the mean of
the dismissed genre vectors. This is a bounded, reversible heuristic, not a learned
plot model; no low ratings or watched history are invented. Candidate filtering
and ranking apply this feedback in every algorithm. It is not part of the offline
rating-only benchmark. Profiles must be explicitly saved to persist across sessions.

The All view reserves roughly half the results for each media type, ranking within
type and filling remaining capacity if a type has too few candidates. This avoids
calibration claims about incompatible TVmaze/movie scales. Single-type rankings
and the film-only evaluation keep their usual candidate order. Sparse KNN has
the original adjusted-cosine formula with bounded intermediates, and no item-square
matrix. Cached component arrays are copied before returning to callers.

## Archived 100K protocol details

## Identity and history

MovieLens's 1,682 catalog rows include 18 duplicate pairs. Only matching source,
IMDb lookup URL, title and year are merged; namesakes with different metadata
remain distinct. The smallest ID represents each identity, with every original ID
retained as an alias. The resulting catalog contains 1,664 films. Old profile IDs,
rated exclusions and hidden exclusions all use the same canonical mapping.

All 100,000 source rating events retain their timestamps through temporal splitting.
At each observation boundary, repeated canonical user/title ratings use the latest
**available** event. Globally removing earlier events in favour of a future update
would leak future information into training. Stable timestamp ordering resolves
same-time ties deterministically. Test relevance is a set of canonical positive
titles not already seen before that boundary.

## Models

Popularity uses `(rating_sum + 20 * global_mean) / (rating_count + 20)`.
Counts and means use only available, latest user/title observations.

Genre features are normalized binary vectors over the union of catalog genres.
TVmaze `Science-Fiction` maps to `Sci-Fi`. The visitor vector is the normalized sum
of `(rating - 3) * title_vector`. Negative signals therefore lower genre scores.
Zero/cancelling vectors fall back to community scores. Explanations identify
observable genre matches and preference weights, not causal latent-factor effects.

Collaborative uses regularized biased matrix factorization with NumPy ALS:
`r_ui ≈ mean + user_bias[u] + item_bias[i] + user_factors[u] · item_factors[i]`.
Only observed interactions enter the squared-error objective. There are 24 factors,
15 ALS iterations, ridge penalties 5, and seed 42. Unseen visitors are folded into
fixed item factors by ridge regression, without retraining. The benchmark uses the
same fold-in path. Missing ratings are not zero-valued targets.

Item-KNN uses user-mean-centred rating vectors and adjusted cosine. Co-rating count
shrinks each similarity by `common / (common + 10)`. Self/negative similarities are
discarded. Up to 40 positively similar rated neighbours contribute to a candidate's
weighted rating residual around the visitor's mean; unsupported candidates use
weighted popularity. This deliberately fixed baseline is not tuned on the test.

Hybrid clips collaborative predictions to [1,5], scales them to [0,1], and blends
with cosine genre scores scaled from [-1,1] to [0,1]:
`alpha * collaborative + (1-alpha) * genre`. Undefined genre preferences use the
scaled collaborative score. Validation selects alpha from `[0,.25,.5,.75,1]`.
Clipping can create ties, so alpha=1 Hybrid need not equal raw Collaborative.
Every model resolves ranking ties by canonical ID. Empty profiles use community
ratings for every model.

## Series and mixed catalogs

Series use negative TVmaze show IDs, avoiding collisions with MovieLens. The
snapshot contains scripted/animated shows from a documented subset of index pages
plus twelve named titles. It is not a complete TVmaze or modern-film catalog.

There are no individual TVmaze viewing interactions in training. Series scores
use `0.75 * scaled_genre_cosine + 0.25 * (TVmaze_average/10)` when a genre preference
exists, and community quality otherwise. Missing averages use an internal neutral
5/10 prior but the UI displays "no community rating". Collaborative and Item-KNN
retain movie scores and use the series fallback, never dummy series factor vectors.

Community/movie fallback scores are rescaled to [1,5] where required for ranking;
Hybrid uses [0,1]. These are mixed-source heuristics, not calibrated predictions.
The UI always displays actual source scales and does not invent series vote counts.
Minimum MovieLens vote count applies to films only. Series ratings can affect the
shared genre profile, but cannot train movie collaborative factors.

## Ranking and variety

One shared candidate filter excludes canonical rated/hidden/watched titles and applies
media type, OR-matched selected genres, release interval and film vote threshold.
Evaluation calls this same filter with films and at least one available rating.

The UI can record watched titles without ratings. They are excluded from candidates
and recognition prompts but never enter training, genre vectors or fold-in as scores.
Watch-later entries do not change model input. Profiles use schema 4, with backward
compatibility for versions 2/3 and the original rating mapping.

For series-only profiles, Hybrid films use 75% rescaled signed genre cosine and
25% rescaled Bayesian MovieLens quality. No movie observations are invented.
Film-rated profiles keep the validation-selected alpha. Series-only ranking is
a disclosed heuristic outside the film-only evaluation below.

Variety zero preserves the model order. Higher values use greedy MMR:
`(1-weight) * candidate_normalized_relevance - weight * max_selected_genre_cosine`.
The first result is the most relevant; later results penalize repetition. Community
ratings shown on cards do not change. The analysis uses weights 0/.25/.5/.75 on one
fixed test cohort, without selecting a default from test results.

## Global temporal protocol

Timestamp groups are partitioned at approximately the 80th and 90th percentiles:
80,003 / 9,997 / 10,000 events. Every validation event follows every train event;
every test event follows all train+validation events. Validation tunes only alpha;
a separate final model trains on train+validation. The full-data app artifact is
never loaded by the evaluator. Other parameters are fixed in advance.

Candidates are the full training-supported catalog with all seen titles excluded.
Held-out ratings >=4 are binary relevance labels. Positives without a past rating
remain in metric denominators. Macro means use warm users with at least one future
positive. There are no sampled negatives or future popularity counts.

The test includes 166 users: 76 have no past history; 13 warm users have no unseen
positive labels. The final cohort is 77 users with 1,544 positive user/title labels,
37 unavailable before the boundary. The supported catalog has 1,622 films.

Precision@10 divides hits by 10 even for a short list. Recall divides by all relevant
titles. NDCG uses log2 discounts and ideal binary ranking length min(10, positives).
Coverage is the fraction of supported films recommended to at least one user.
Diversity is average pairwise `1-cosine` genre distance (zero for lists shorter than 2).

## Uncertainty and onboarding

Bootstrap intervals use 1,000 samples of users with replacement, seed 42, with
identical indices across algorithms. Percentiles 2.5/97.5 yield intervals for the
three ranking metrics. Paired NDCG differences against Popularity are recorded too.
This quantifies variation across this cohort; it does not cover dataset selection
bias, parameter randomness or future deployment conditions. Overlapping separate
intervals alone are not a statistical test.

The onboarding experiment uses 76 matched users with at least ten distinct past
ratings and unseen future positive titles. Their **entire histories** are removed
from background model training (791 remaining users). Last 3, 5 or 10 pre-boundary
ratings are seeds. Only seeds are supplied and excluded from candidates, matching
what the app knows. Previously seen non-seed titles can consume recommendation
slots but are not labelled as new relevant results. Future labels exclude all
past seen titles; unavailable positives remain in denominators. Users and future
labels are fixed across seed lengths. Series are absent from every benchmark.

## Limits

Historical explicit ratings have selection bias. Unobserved titles are not proven
dislikes. The warm cohort is small, and popularity is strong in this split. Default
models are not claimed to beat it reliably. Onboarding results do not guarantee
monotonic improvement or live satisfaction. TV-series ranking has no measured
interaction benchmark. MovieLens films end in 1998 and genre-only content does
not understand plots, actors or directors.
