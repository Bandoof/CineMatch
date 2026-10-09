# Measured benchmark — protocol 2

Global chronological 80/10/10 split with timestamp ties. Validation-only ALS/Hybrid tuning. Full past-supported film catalog, all known titles excluded, unseen future rating >=4 relevant. User namespaces kept separate. App artifacts never used by evaluation. Series and not-interested feedback are not evaluated. Development snapshot; not comparable to the original 100K benchmark.

Canonical films: 10123; source events: 200836.
Latest available user/title ratings enter training only after splitting.
Series are not evaluated here.

Hybrid alpha: **1.0**, selected by validation NDCG@10.

Warm test cohort: **28 users**.

| Model | Precision@10 | Recall@10 | NDCG@10 | Coverage | Diversity |
|---|---:|---:|---:|---:|---:|
| Hybrid | 0.0607 | 0.0298 | 0.0563 | 0.0128 | 0.7651 |
| Collaborative | 0.0464 | 0.0214 | 0.0408 | 0.0159 | 0.7428 |
| Item-KNN | 0.0036 | 0.0018 | 0.0039 | 0.0298 | 0.7370 |
| Content-based | 0.0036 | 0.0005 | 0.0079 | 0.0209 | 0.0867 |
| Popularity | 0.0607 | 0.0251 | 0.0679 | 0.0035 | 0.7818 |

## 95% paired user bootstrap intervals

1,000 samples, seed 42; identical user draws across models.

| Model | NDCG@10 interval | NDCG minus Popularity interval |
|---|---:|---:|
| Hybrid | 0.0236 – 0.0990 | -0.0324 – +0.0080 |
| Collaborative | 0.0164 – 0.0742 | -0.0604 – +0.0008 |
| Item-KNN | 0.0000 – 0.0118 | -0.1256 – -0.0157 |
| Content-based | 0.0000 – 0.0236 | -0.1093 – -0.0206 |
| Popularity | 0.0225 – 0.1277 | +0.0000 – +0.0000 |

## New-user onboarding

Matched users with >=10 past ratings. Last N ratings before the test boundary are seeds. Entire target-user histories are removed from model training. Full supported candidates exclude seeds only; future positives exclude all previously seen titles.

Matched users: 28; background training users: 1437.

| Seed ratings | Model | Recall@10 | NDCG@10 |
|---:|---|---:|---:|
| 3 | Hybrid | 0.0171 | 0.0323 |
| 3 | Collaborative | 0.0164 | 0.0282 |
| 3 | Item-KNN | 0.0057 | 0.0084 |
| 3 | Content-based | 0.0000 | 0.0000 |
| 3 | Popularity | 0.0231 | 0.0533 |
| 5 | Hybrid | 0.0189 | 0.0374 |
| 5 | Collaborative | 0.0177 | 0.0304 |
| 5 | Item-KNN | 0.0025 | 0.0057 |
| 5 | Content-based | 0.0000 | 0.0000 |
| 5 | Popularity | 0.0231 | 0.0533 |
| 10 | Hybrid | 0.0182 | 0.0385 |
| 10 | Collaborative | 0.0086 | 0.0229 |
| 10 | Item-KNN | 0.0029 | 0.0050 |
| 10 | Content-based | 0.0045 | 0.0092 |
| 10 | Popularity | 0.0231 | 0.0533 |

## Fixed-cohort quality/variety analysis

Default weight remains zero; test analysis does not select it.

| MMR weight | NDCG@10 | Diversity | Coverage |
|---:|---:|---:|---:|
| 0 | 0.0563 | 0.7651 | 0.0128 |
| 0.25 | 0.0418 | 0.9514 | 0.0119 |
| 0.5 | 0.0292 | 0.9991 | 0.0109 |
| 0.75 | 0.0292 | 1.0000 | 0.0110 |

Historical results do not guarantee live satisfaction or series quality.
The full-data app model is never used by this evaluation.

## Expanded configuration and same-cohort comparison

Dataset: MovieLens 100K + latest-small pinned development snapshot.
Official archive SHA-256: `696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436`.

ALS: 32 factors, regularization 10;
Hybrid community-quality weight 0.4.
Chronological split: 160668 / 20084 / 20084.

| Model on the same expanded data | Precision@10 | Recall@10 | NDCG@10 | Coverage |
|---|---:|---:|---:|---:|
| Previous default architecture | 0.0536 | 0.0216 | 0.0582 | 0.0208 |
| Updated validation-selected architecture | 0.0607 | 0.0298 | 0.0563 | 0.0128 |

Paired 95% NDCG difference interval: [-0.02601880267539613, 0.01837109187543708].
It includes zero; no reliable overall accuracy improvement is established.
More relevant items accompany slightly lower ranked relevance and coverage.
This development snapshot is separate from the archival 100K benchmark.
Series, media balancing and not-interested feedback are not measured here.
