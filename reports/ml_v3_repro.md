# MovieLens 1M protocol 3 — reproduction

Generated: 2026-11-15T18:59:23.709230+00:00 by `python -m scripts.reproduce_ml_v3` in 44 s. Recorded evidence: [ml_v3.json](ml_v3.json) (2026-10-09T09:01:09.182777+00:00).

## Inputs

| Input | Recorded | Reproduction | Same |
|---|---|---|---|
| MovieLens 1M ZIP SHA-256 | `a6898adb50b9…` | `a6898adb50b9…` | True |
| Content snapshot SHA-256 | `903ac59408da…` | `7a007e1c8332…` | False |
| events / catalog / split | | | True |
| validation users (IDs) | | | True |
| test users (IDs) | | | True |
| ALS parameters | | | True |

## Selected policy (ALS, LSA, quality)

| Seed ratings | Recorded | Reproduction |
|---|---|---|
| 3 | [0.25, 0.25, 0.5] | [0.5, 0.25, 0.25] |
| 5 | [0.0, 0.0, 1.0] | [0.0, 0.0, 1.0] |
| 10 | [0.0, 0.0, 1.0] | [0.0, 0.0, 1.0] |

## Recorded vs reproduced (tolerance 1e-06)

| Seeds | Model | NDCG@10 recorded | NDCG@10 reproduced | Max |Δ| (all metrics) | Status |
|---:|---|---:|---:|---:|---|
| 3 | Popularity | 0.0657 | 0.0657 | 0.00e+00 | match |
| 3 | Collaborative | 0.0614 | 0.0614 | 0.00e+00 | match |
| 3 | Semantic | 0.0258 | 0.0269 | 2.25e-02 | differs (content snapshot) |
| 3 | Genres | 0.0186 | 0.0186 | 0.00e+00 | match |
| 3 | Adaptive | 0.0744 | 0.0736 | 2.77e-01 | differs (content snapshot) |
| 5 | Popularity | 0.0657 | 0.0657 | 0.00e+00 | match |
| 5 | Collaborative | 0.0659 | 0.0659 | 0.00e+00 | match |
| 5 | Semantic | 0.0317 | 0.0319 | 7.06e-03 | differs (content snapshot) |
| 5 | Genres | 0.0167 | 0.0167 | 0.00e+00 | match |
| 5 | Adaptive | 0.0657 | 0.0657 | 0.00e+00 | match |
| 10 | Popularity | 0.0663 | 0.0663 | 0.00e+00 | match |
| 10 | Collaborative | 0.0684 | 0.0684 | 0.00e+00 | match |
| 10 | Semantic | 0.0359 | 0.0363 | 3.35e-03 | differs (content snapshot) |
| 10 | Genres | 0.0187 | 0.0187 | 0.00e+00 | match |
| 10 | Adaptive | 0.0663 | 0.0663 | 0.00e+00 | match |

Paired Adaptive − Popularity NDCG@10, 95% interval:

| Seeds | Recorded | Reproduced |
|---:|---|---|
| 3 | [+0.0031, +0.0144] | [+0.0019, +0.0140] |
| 5 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |
| 10 | [+0.0000, +0.0000] | [+0.0000, +0.0000] |

## All metrics with 95% user-bootstrap intervals (reproduction)

600 test users, 1000 resamples, seed 42. Catalog coverage is shown without an interval: it is a union over users, not a per-user mean, so a with-replacement user bootstrap (~63% distinct users per resample) biases it downward and is not a valid interval.

### After 3 seed ratings

| Model | Recall@10 | NDCG@10 | Coverage | Novelty (bits) | Diversity |
|---|---|---|---|---|---|
| Popularity | 0.0215 [0.0167, 0.0269] | 0.0657 [0.0559, 0.0757] | 0.0031 | 9.6053 [9.6042, 9.6063] | 0.8416 [0.8412, 0.8420] |
| Collaborative | 0.0205 [0.0161, 0.0258] | 0.0614 [0.0519, 0.0711] | 0.0209 | 9.9325 [9.9114, 9.9565] | 0.7838 [0.7802, 0.7873] |
| Semantic | 0.0086 [0.0055, 0.0130] | 0.0269 [0.0210, 0.0327] | 0.5483 | 12.5019 [12.3545, 12.6589] | 0.3621 [0.3419, 0.3808] |
| Genres | 0.0039 [0.0022, 0.0062] | 0.0186 [0.0140, 0.0230] | 0.2423 | 12.7025 [12.6090, 12.8016] | 0.1612 [0.1400, 0.1810] |
| Adaptive | 0.0253 [0.0203, 0.0310] | 0.0736 [0.0629, 0.0840] | 0.0404 | 9.9500 [9.9175, 9.9873] | 0.6923 [0.6852, 0.7002] |

Paired difference vs Popularity, 95% interval:

| Model | Recall@10 | NDCG@10 | Novelty (bits) | Diversity |
|---|---|---|---|---|
| Collaborative | [-0.0035, +0.0012] | [-0.0095, +0.0008] | [+0.3063, +0.3513] | [-0.0614, -0.0541] |
| Semantic | [-0.0187, -0.0065] | [-0.0485, -0.0283] | [+2.7498, +3.0537] | [-0.4998, -0.4608] |
| Genres | [-0.0232, -0.0122] | [-0.0570, -0.0376] | [+3.0036, +3.1963] | [-0.7018, -0.6604] |
| Adaptive | [-0.0007, +0.0079] | [+0.0019, +0.0140] | [+0.3124, +0.3827] | [-0.1565, -0.1412] |

### After 5 seed ratings

| Model | Recall@10 | NDCG@10 | Coverage | Novelty (bits) | Diversity |
|---|---|---|---|---|---|
| Popularity | 0.0215 [0.0167, 0.0269] | 0.0657 [0.0559, 0.0757] | 0.0033 | 9.6053 [9.6038, 9.6066] | 0.8420 [0.8415, 0.8425] |
| Collaborative | 0.0217 [0.0172, 0.0268] | 0.0659 [0.0561, 0.0757] | 0.0255 | 9.9565 [9.9327, 9.9845] | 0.7730 [0.7688, 0.7771] |
| Semantic | 0.0074 [0.0056, 0.0095] | 0.0319 [0.0258, 0.0384] | 0.5457 | 12.3904 [12.2391, 12.5378] | 0.3480 [0.3308, 0.3664] |
| Genres | 0.0025 [0.0018, 0.0033] | 0.0167 [0.0123, 0.0213] | 0.2421 | 12.9520 [12.8539, 13.0555] | 0.1146 [0.0981, 0.1311] |
| Adaptive | 0.0215 [0.0167, 0.0269] | 0.0657 [0.0559, 0.0757] | 0.0033 | 9.6053 [9.6038, 9.6066] | 0.8420 [0.8415, 0.8425] |

Paired difference vs Popularity, 95% interval:

| Model | Recall@10 | NDCG@10 | Novelty (bits) | Diversity |
|---|---|---|---|---|
| Collaborative | [-0.0024, +0.0024] | [-0.0057, +0.0055] | [+0.3274, +0.3791] | [-0.0733, -0.0647] |
| Semantic | [-0.0201, -0.0088] | [-0.0450, -0.0231] | [+2.6329, +2.9323] | [-0.5110, -0.4756] |
| Genres | [-0.0246, -0.0139] | [-0.0590, -0.0388] | [+3.2484, +3.4498] | [-0.7438, -0.7110] |
| Adaptive | [+0.0000, +0.0000] | [+0.0000, +0.0000] | [+0.0000, +0.0000] | [+0.0000, +0.0000] |

### After 10 seed ratings

| Model | Recall@10 | NDCG@10 | Coverage | Novelty (bits) | Diversity |
|---|---|---|---|---|---|
| Popularity | 0.0217 [0.0169, 0.0271] | 0.0663 [0.0565, 0.0765] | 0.0036 | 9.6061 [9.6035, 9.6086] | 0.8431 [0.8424, 0.8438] |
| Collaborative | 0.0204 [0.0160, 0.0257] | 0.0684 [0.0585, 0.0785] | 0.0371 | 9.9593 [9.9264, 9.9931] | 0.7555 [0.7502, 0.7612] |
| Semantic | 0.0093 [0.0071, 0.0116] | 0.0363 [0.0295, 0.0431] | 0.4746 | 12.3387 [12.1995, 12.4917] | 0.3557 [0.3367, 0.3742] |
| Genres | 0.0042 [0.0027, 0.0064] | 0.0187 [0.0140, 0.0243] | 0.2470 | 12.9737 [12.8807, 13.0715] | 0.0782 [0.0670, 0.0899] |
| Adaptive | 0.0217 [0.0169, 0.0271] | 0.0663 [0.0565, 0.0765] | 0.0036 | 9.6061 [9.6035, 9.6086] | 0.8431 [0.8424, 0.8438] |

Paired difference vs Popularity, 95% interval:

| Model | Recall@10 | NDCG@10 | Novelty (bits) | Diversity |
|---|---|---|---|---|
| Collaborative | [-0.0046, +0.0016] | [-0.0048, +0.0087] | [+0.3207, +0.3858] | [-0.0930, -0.0817] |
| Semantic | [-0.0182, -0.0071] | [-0.0411, -0.0191] | [+2.5922, +2.8833] | [-0.5066, -0.4691] |
| Genres | [-0.0234, -0.0121] | [-0.0578, -0.0376] | [+3.2755, +3.4648] | [-0.7764, -0.7535] |
| Adaptive | [+0.0000, +0.0000] | [+0.0000, +0.0000] | [+0.0000, +0.0000] | [+0.0000, +0.0000] |

## Scope

Simulated new users; entire target histories removed from background training. Last N pre-boundary ratings are seeds. Full catalog candidates exclude seeds; positives exclude all earlier history. 300 validation / max 600 test users selected by fixed ID hash. Current Wikipedia/TVmaze metadata is retrospective; not an as-of historical metadata guarantee. Series/negative-feedback/live satisfaction not measured. Mixing policy transfers to the separate expanded app; deployment quality must be checked independently.

Novelty and coverage are not accuracy. An interval that includes zero means no established difference. User ID lists are not stored here (MovieLens 1M may not be redistributed without permission); their SHA-256 is compared instead.
