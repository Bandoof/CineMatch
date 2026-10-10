# CineMatch v1.2 — engineering release preparation

This milestone integrates engineering and research infrastructure. No version
tag or GitHub Release is published by this preparation. It releases no newly
validated recommendation policy or trained research model.

## Included capabilities

- A pinned MovieLens 1M protocol with archive/file checksums, timestamp-tie-safe
  splits and disjoint 171-user validation / 326-user test cohorts. Both cohorts
  are excluded from background training; historical v3 targets are excluded.
- Validation-only ALS, fold-in, content, calibration and blend experiments,
  followed by frozen-selection/source checks and exclusive final-access markers.
- TF-IDF and LSA research, plus optional pinned multilingual MiniLM ONNX inference
  on CPU. Standard application installs do not require these optional packages.
- Ukrainian and English recommendation explanations tied to actual score
  contributions and disclosed heuristic adjustments. Research models do not
  become production defaults; numerical attribution is not an enjoyment probability.
- Synthetic regression coverage for research isolation, protocol safeguards,
  explanation fidelity, recommendation equivalence and existing profile workflows.
- Read-only evidence verification, original-byte preservation across Windows and
  Linux checkouts, dependency auditing and CodeQL checks.

The changes are integrated through PRs [#12](https://github.com/Bandoof/CineMatch/pull/12),
[#13](https://github.com/Bandoof/CineMatch/pull/13),
[#14](https://github.com/Bandoof/CineMatch/pull/14) and
[#15](https://github.com/Bandoof/CineMatch/pull/15), preserving their Git history.
Exact commits and current checks are available on those PRs and in
[GitHub Actions](https://github.com/Bandoof/CineMatch/actions).

## Evidence and research limits

The interrupted experiment's reported **+17.8% NDCG@10 gain is unverified**.
Original validation trials, frozen selection and final/per-user outputs were not
recovered. Implemented search spaces, verified input hashes and passing synthetic
tests do not establish model quality. No accuracy improvement is advertised.

Treat the previously accessed 326-user final cohort as consumed. Do not reuse it
for model selection or present a rerun as a fresh holdout. The historical v3
validation/test target overlap of 199 users makes those inspected outcomes
development evidence for v1.2. TV-series quality, live satisfaction and onboarding
gains remain unbenchmarked. Production ranking stays under its existing policy.

The [recovery report](../reports/ml_v12.md),
[research protocol](ml-v12-research.md) and [model card](ml-v12-model-card.md)
retain the interrupted experiment and distinguish verified facts from attributed
claims. Dated recovery receipts are historical snapshots, not claims about later
merge or release status. Historical benchmark files are preserved byte-for-byte.

## Verification and next milestone

Before publication, verify the exact integrated `main` revision with full pytest,
Ruff, configured Mypy, pre-commit, dependency audits, Linux/Windows CI and CodeQL.
Use synthetic data and an isolated temporary profile database for application
startup, profile persistence and bilingual UI checks. Record optional real CPU
encoder tests separately from ordinary CI, which skips them without a model cache.
Container and graphical browser checks must be reported only when actually run.

Public input verification requires no training or holdout evaluation:

```bash
python -m scripts.verify_v12_evidence
```

The next research milestone is recovery and independent audit of original outputs,
if available, or a preregistered experiment with a genuinely unused test cohort,
preferably external data. Production promotion requires reproducible evidence
and a separate decision. A version tag and GitHub Release require separate authorization.
