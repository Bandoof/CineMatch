# CineMatch content / Adaptive model card

## Intended use

Local movie/series discovery, demonstration of classical recommendation methods,
and an auditable ML portfolio. Inputs are voluntarily supplied star ratings and
explicit exclusions; no viewing events are invented. Scores are ranking signals,
not probabilities that a visitor will like a title.

## Trained models

- Biased ALS matrix factorisation: 32 factors, 15 epochs, regularisation 10,
  random seed 42; observed explicit film ratings only. New profiles use ridge
  fold-in against fixed item factors, rather than retraining the entire model.
- Content model: sublinear TF-IDF, Unicode accent normalisation, unigram/bigram
  vocabulary capped at 24,000 features; source titles, Ukrainian titles, repeated
  genres and source English/Ukrainian lead descriptions. Randomised TruncatedSVD
  learns up to 64 latent dimensions, seed 42 and five power iterations. Embeddings
  and signed rating-weighted user vectors are normalised. Ratings are centred at 3.
  Tiny corpora use sparse TF-IDF directly. This is LSA, **not a Transformer**.
- Adaptive combines rescaled ALS, content cosine and Bayesian community quality.
  Fifteen quarter-step mixtures are compared separately at 3/5/10 seeds, using
  validation NDCG@10. The same fixed user cohort is used for all seed lengths.
  In the app, <=3 ratings use the 3-seed policy, 4–7 the 5-seed policy, >=8 the
  10-seed policy. Interpolation buckets and transfer to the separate expanded app
  have not themselves been evaluated. Missing/invalid/stale policies use film quality.

Descriptions match the source catalog ID **and original title**, or an unambiguous
normalised title/year when the independent dataset uses different native IDs.
This prevents applying an unrelated record or remake to a movie. Source URLs are
restricted to Wikipedia/TVmaze. Missing Ukrainian descriptions explicitly fall
back to English source text. English and Ukrainian features share a learned
document representation; cross-language retrieval is not guaranteed for arbitrary
synonyms or rare tokens. There are no generated plots or invented cast credits.

## Independent experiment

`python -m scripts.download_benchmark` downloads the official MovieLens 1M archive
and records its SHA-256. A subsequent changed archive is rejected. Only movies,
ratings and README are extracted; demographic fields are not used.

`python -m scripts.benchmark_v3` defines global 80/10/10 timestamp boundaries;
ties stay on one side. Repeated user/title events are consolidated only inside
each past boundary. A target needs at least ten unique past ratings and an unseen
future positive (>=4). Deterministic SHA-256 user ordering selects at most 300
validation and 600 test targets without selecting by model outcome. The same
person can appear at different validation/test boundaries; test labels are never
used to select mixtures. Every target user's entire past history is removed from
the relevant background model, and only the last N pre-boundary ratings are used
for fold-in. Vocabulary and LSA are fitted on background-supported items only.

The full canonical 1M catalog is ranked, including unsupported items. Candidates
exclude seeds; positives exclude every earlier viewed title. Previously watched
non-seed titles can consume recommendation slots, matching an incomplete new
visitor profile. Unavailable positives remain in recall/NDCG denominators. No
sampled negatives or future rating-count features are used. Popularity, ALS,
LSA, genre cosine and Adaptive use identical candidates and relevant labels.

Precision divides hits by 10; recall divides by all future positives; NDCG uses
binary relevance and log2 discount. Coverage divides the union of recommendations
by the entire canonical catalog. Diversity is mean pairwise genre cosine distance.
Novelty is mean negative log2 of add-one-smoothed past item-vote probability,
measured in bits; it is not a relevance metric. Unobserved items are not proven dislikes.

Paired bootstrap resamples 1,000 sets of users with replacement, seed 42, using
the same draws for every algorithm. Reports include 95% percentile intervals
and Adaptive-minus-Popularity NDCG differences. The final ALS/content model is
refitted on train+validation background without the selected test users.

**Text is retrospective.** Current Wikipedia/TVmaze snapshots can contain facts
published after rating boundaries. The experiment does not establish performance
with historically available descriptions. Raw ratings remain chronologically
separated; content results must retain this qualification.

The app catalog and background interactions differ from the 1M experiment.
Transferring a mixing policy is explicitly disclosed. 1M numbers are not app,
mixed-catalog or series accuracy. Old 100K/expanded reports are archived separately.

## Feedback and explanations

Title-only feedback excludes that ID without changing others' scores. Topic
feedback additionally subtracts up to 20% of the algorithm's normal scale for
shared genres and 10% for positive cosine with dismissed content. The direction
is averaged across topics. This hand-set discount is not a learned interaction
model and has no measured satisfaction effect. Temporary skips live only in the
session. No action becomes a synthetic low rating. Profile schema 5 stores
`topic_blocked` separately; old `blocked` imports retain legacy topic meaning.

Topic search blends 75% description similarity with 25% min/max-rescaled current
model relevance. It is a separate hand-set retrieval control, not the validation
policy. All candidates still respect exclusions, filters and variety settings.
Unrecognised requests leave the original scores intact and display a notice.

Text explanations expose actual shared TF-IDF terms with a highly rated seed;
they do not claim to explain ALS factors or the complete blend. Before/after lists
use the same current filters and model, holding the previous profile/exclusions
as a session snapshot. Count of changed Top-10 titles is not an accuracy metric.

The recognition guide begins with familiar anchors. After >=3 ratings it may
choose a less-covered theme from its first 80 candidates using recognition reach,
absolute content affinity and genre coverage. This is an exploration heuristic,
not calibrated uncertainty or proven active-learning improvement. Neutral 'not
seen' answers never change recommendation scores.

## Limits and next evidence needed

Series have no individual interaction dataset and use content/community heuristics.
Models are affected by explicit-rating selection bias and historical catalogs.
There is no measured online engagement, conversational intent model, calibrated
preference probability, semantic Transformer, causal explanation, or external
account system. Stronger claims require historical metadata snapshots, a separate
deployment evaluation and real consented interaction logs with time-aware tests.
“10/10 ML” is not a measured result; claims must follow the evidence.

## Artifacts

[Measured report](../reports/ml_v3.md), [JSON](../reports/ml_v3.json),
[CSV](../reports/ml_v3.csv). JSON records source checksum, split boundaries,
target IDs, all validation trials, final policy, model dimensions, content snapshot
hash and runtime. Data/models/personal profiles are excluded from the source ZIP.

Sources: [MovieLens 1M](https://grouplens.org/datasets/movielens/1m/),
[TF-IDF](https://scikit-learn.org/1.5/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html),
[TruncatedSVD](https://scikit-learn.org/1.5/modules/generated/sklearn.decomposition.TruncatedSVD.html),
[Wikipedia extracts](https://www.mediawiki.org/wiki/Extension:TextExtracts),
[TVmaze licensing](https://www.tvmaze.com/api#licensing).
