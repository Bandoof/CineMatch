# Measured benchmark — protocol 2

Global temporal split; full training-supported catalog; all seen items excluded; rating >=4 relevant; macro mean over warm users with positives; unavailable positives remain in recall/NDCG denominators; new user fold-in.

Canonical films: 1664; source events: 100000.
Latest available user/title ratings enter training only after splitting.
Series are not evaluated here.

Hybrid alpha: **1.0**, selected by validation NDCG@10.

Warm test cohort: **77 users**.

| Model | Precision@10 | Recall@10 | NDCG@10 | Coverage | Diversity |
|---|---:|---:|---:|---:|---:|
| Hybrid | 0.0818 | 0.0393 | 0.1017 | 0.1628 | 0.6770 |
| Collaborative | 0.0831 | 0.0396 | 0.1072 | 0.1628 | 0.6767 |
| Item-KNN | 0.0260 | 0.0256 | 0.0322 | 0.2324 | 0.7609 |
| Content-based | 0.0558 | 0.0395 | 0.0545 | 0.1523 | 0.1346 |
| Popularity | 0.1091 | 0.0828 | 0.1217 | 0.0271 | 0.7327 |

## 95% paired user bootstrap intervals

1,000 samples, seed 42; identical user draws across models.

| Model | NDCG@10 interval | NDCG minus Popularity interval |
|---|---:|---:|
| Hybrid | 0.0590 – 0.1485 | -0.0484 – +0.0087 |
| Collaborative | 0.0633 – 0.1550 | -0.0447 – +0.0154 |
| Item-KNN | 0.0132 – 0.0546 | -0.1270 – -0.0537 |
| Content-based | 0.0294 – 0.0863 | -0.1062 – -0.0305 |
| Popularity | 0.0809 – 0.1663 | +0.0000 – +0.0000 |

## New-user onboarding

Matched users with >=10 past ratings. Last N ratings before the test boundary are seeds. Entire target-user histories are removed from model training. Full supported candidates exclude seeds only; future positives exclude all previously seen titles.

Matched users: 76; background training users: 791.

| Seed ratings | Model | Recall@10 | NDCG@10 |
|---:|---|---:|---:|
| 3 | Hybrid | 0.0475 | 0.0906 |
| 3 | Collaborative | 0.0475 | 0.0906 |
| 3 | Item-KNN | 0.0208 | 0.0525 |
| 3 | Content-based | 0.0079 | 0.0402 |
| 3 | Popularity | 0.0184 | 0.0800 |
| 5 | Hybrid | 0.0594 | 0.0976 |
| 5 | Collaborative | 0.0594 | 0.0976 |
| 5 | Item-KNN | 0.0080 | 0.0294 |
| 5 | Content-based | 0.0239 | 0.0390 |
| 5 | Popularity | 0.0184 | 0.0800 |
| 10 | Hybrid | 0.0585 | 0.0962 |
| 10 | Collaborative | 0.0585 | 0.0967 |
| 10 | Item-KNN | 0.0083 | 0.0249 |
| 10 | Content-based | 0.0261 | 0.0354 |
| 10 | Popularity | 0.0184 | 0.0802 |

## Fixed-cohort quality/variety analysis

Default weight remains zero; test analysis does not select it.

| MMR weight | NDCG@10 | Diversity | Coverage |
|---:|---:|---:|---:|
| 0 | 0.1017 | 0.6770 | 0.1628 |
| 0.25 | 0.0912 | 0.9427 | 0.1424 |
| 0.5 | 0.0696 | 0.9989 | 0.1289 |
| 0.75 | 0.0679 | 1.0000 | 0.1289 |

Historical results do not guarantee live satisfaction or series quality.
The full-data app model is never used by this evaluation.
