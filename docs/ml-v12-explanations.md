# Faithful explanations (v1.2)

The deployed algorithms/policy are unchanged by the research pipeline. These
application fixes correct misleading explanations without changing scores:

- Adaptive's 100% community-quality buckets explicitly say community quality;
  they no longer imply ALS/content personalization. Rated-title exclusion still
  applies. Mixed buckets show actual weights and additive base-score terms.
- Missing/cancelled content vectors are counted as quality contributions. Series
  and series-only fallbacks do not acquire fictional collaborative observations.
- Semantic displays up to one positive and one negative **actual cosine term**
  from observed ratings. All signed terms sum to the unscaled content cosine;
  displayed examples are a partial decomposition, not the entire final score.
- Hybrid no longer presents a shared-genre match when the genre weight is zero.
- Actual topic-discount amounts are labelled heuristic. Variety reordering is
  disclosed separately. Query blends retain their own description.

Terms are deterministic numerical attribution, not a causal explanation, a
probability of enjoyment, Transformer-generated text or proof of better quality.
ALS terms explain its weighted score in a composite, not why a latent factor
matches a user's interests. Descriptions are mentioned only as available inputs.
English/Ukrainian use the same numbers; title names follow existing metadata.

Regression tests check additive equality against real scoring, negative/positive
rating terms, pure-quality policies, neutral-vector fallbacks, series profiles,
cache immutability and the v1.1 single-context explanation performance invariant.
Existing profile, Undo, watched/watchlist, dismissal and autosave tests remain.
