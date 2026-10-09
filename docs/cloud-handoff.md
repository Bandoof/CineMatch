# CineMatch: context for cloud continuation

The owner is Bandoof. The user asked to continue work in cloud Codex through a
public GitHub repository. This document carries the implementation state and
remaining product priorities; it is not a full copy of the local conversation.

## User intent

Build a credible Junior ML/AI Engineer portfolio project: movie and series
recommendations, polished Ukrainian/English UI, posters and verified Ukrainian
titles, recognition-based taste onboarding, Watch later, Already watched,
meaningful Not interested feedback, automatic local memory, neutral error pages.
The latest requested upgrade emphasised real machine learning and visible proof
of its quality. Do not invent experience, projects, translations or accuracy.

## Current implementation

- Streamlit, seven algorithms: Popularity, genre content, ALS, item-KNN, Hybrid,
  learned TF-IDF/64-dimensional LSA and Adaptive. See the model card.
- Three destinations: For you, My library, ML Lab. Source descriptions, optional
  topic search, title-only/topic/session feedback and undo, real before/after lists.
- Expanded catalog: 10,123 films and 602 series; 6,435 verified Ukrainian names.
  Requested Dark Knight, Intouchables/1+1, Interstellar and Leon are present.
- SQLite local autosave with optimistic concurrency; version 5 JSON imports,
  named profiles and old formats retained. Demo state never replaces real memory.
- Public wrapper catches application errors and offers a neutral retry page.
  Maintenance mode is separate; a stopped server needs hosting-level fallback.

## Evidence and scope

Final local Windows/Python 3.10: 61 tests passed; Linux/Docker/Python 3.11:
61 tests passed. Ruff passed on both. No remote CI result is inferred from this.

Independent MovieLens 1M protocol 3: 1,000,209 events, 300 validation and 600 test
targets, global chronological split, target histories excluded from background
training, last 3/5/10 past ratings as seeds, full-catalog ranking. Validation-only
mixture selection. Adaptive 3-seed NDCG@10: 0.07439285 vs Popularity 0.06566868
(+13.3% relative); paired delta interval [+0.00305867, +0.01438752]. At 5/10 seeds
the selected policy equals Popularity. Current content is retrospective. Test
numbers are not app deployment or series accuracy. Feedback/guide controls are
explicit heuristics, not proven learned active-learning models. Do not claim 10/10.

Reports and checksums: reports/ml_v3.md/json/csv; full protocol and limitations:
docs/ml-v3-model-card.md; local execution record: docs/verification.md.

## Setup

Use Python 3.10/3.11, requirements-dev.txt for checks; set OPENBLAS_NUM_THREADS=1.
Run `python -m pytest -q` and `python -m ruff check .` first. Tests use synthetic
fixtures and need no private profiles or network. Run data/download/training
commands in README only when actual app data are needed. PyArrow is pinned to
25.0.1 for NumPy 1.26 compatibility.

Source excludes data, trained models, secrets and all personal profiles. The
owner's existing local database must stay on their PC. Do not turn this shared
SQLite installation into public multi-user storage: set CINEMATCH_LOCAL_PROFILES=0
for shared hosting until authenticated private storage is built.

The recorded public description snapshot has SHA-256
903ac59408daa2fb4e9563fc178f25cc507785860e51456b15c2ff5ff0e54fec.
It is available as a separate local artifact, CineMatch-content-snapshot.zip,
with per-record attribution. Fresh source downloads can change this fingerprint;
do not relabel old metrics as a fresh run. MovieLens has separate source terms.

## Useful next work

1. Inspect repository and remote CI; reproduce checks before changing anything.
2. Measure the actual application catalog and historically available text; add
   an appropriate real series-interaction benchmark before series accuracy claims.
3. Compare multilingual embeddings/reranking against existing baselines, retaining
   a held-out chronological test and admitting negative or neutral results.
4. Test keyboard/accessibility and user-facing navigation; validate design with
   actual users rather than adding decorative metric badges.
5. Add authenticated storage and hosting-level failure handling if the user asks
   for public deployment. Cloud coding is not itself website deployment.

The original local app runs at http://127.0.0.1:8501 on the owner's PC. A cloud
task's localhost points to its own workspace; it cannot access that local server
or personal database automatically.
