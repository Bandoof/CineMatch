# Development / Розробка

## Isolated setup

Clone the repository and create an environment with Python 3.10 or 3.11:

```bash
git clone https://github.com/Bandoof/CineMatch.git
cd CineMatch
python -m venv .venv
```

On Unix use `source .venv/bin/activate`. On Windows use the interpreter directly:
`.venv\Scripts\python.exe`; no PowerShell execution-policy change is necessary.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m pytest -q --cov=app --cov=src --cov=scripts --cov-report=term-missing
python -m pip_audit -r requirements-dev.txt
```

Set `OPENBLAS_NUM_THREADS=1` before numerical tests for predictable timing.
CI covers Linux Python 3.10/3.11 and Windows Python 3.11. Coverage is measured,
not claimed as a proxy for correctness and not forced to an arbitrary percentage.
Tests use generated data and temporary files; they require no catalog download or
owner profile. The historical [verification](verification.md) records earlier runs;
new PRs must record their own evidence.

## Local product setup

For a minimal film installation, run `python -m scripts.download_data`, then
`python -m scripts.train`, then:

```bash
python -m streamlit run app/streamlit_app.py --server.address=127.0.0.1
```

The expanded catalog, series, verified Ukrainian names and content need the additional
explicit download/train steps in [README](../README.md#run-locally). Downloads require
network access and may take time. Do not run setup inside an existing personal data
folder for tests. Use the `CINEMATCH_DATA_DIR`, `CINEMATCH_PROFILE_DB` and artifact
paths documented in the README when isolating installations. Disable local profiles
and autosave for disposable smoke runs; never import demo ratings into real autosave.

## Review discipline

Keep behavioral changes small; test legacy profiles and both languages. Avoid bulk
formatting of the large UI while fixing unrelated behavior. Numerical changes need
formula-equivalence tests or a separately designed ML experiment. Pin dependency
updates, run the resolver audit and check CI; Dependabot opens proposals, not approvals.
Docker commands in the README provide another environment when Docker is available.

Українською: спочатку запустіть тести на синтетичних даних. Каталоги для локального
застосунку завантажуються окремо; особиста база для тестів не потрібна.

## Incremental quality checks

```bash
python -m ruff check --select I src/profile_actions.py src/hybrid.py src/ranking.py
python -m ruff format --check src/profile_actions.py src/hybrid.py src/ranking.py tests/test_profile_actions.py tests/test_state_reliability.py
python -m mypy
python -m pre_commit install
python -m pre_commit run --all-files
```

Use `ruff format` on the listed files to apply formatting. These pure modules are
strictly typed; UI session-state values remain an explicit dynamic boundary. General
Ruff checks cover the repository; import-order/format checks grow incrementally.
The local pre-commit hooks use tools pinned in requirements-dev, without fetching
hook implementations. Install them in the active environment before committing.
