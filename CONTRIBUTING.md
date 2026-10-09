# Contributing / Як долучитися

Use Python 3.10 or 3.11. Follow [development setup](docs/development.md).
Discuss substantial product or ML changes in an issue first; small fixes may go
straight to a pull request. Keep changes focused and explain the observable problem.

## Before opening a PR

- Reproduce the problem with synthetic data; add a regression test for a bug.
- Run pytest, Ruff and the dependency audit commands in the development guide.
- Keep Ukrainian and English messages consistent; preserve legacy JSON imports.
- Describe validation and remaining limitations in the PR template.
- Keep downloaded data, numeric models, SQLite profiles, logs and secrets out of Git.
- Treat public benchmark results as historical measurements, not live accuracy.
  ML changes require an independent validation/test protocol and a model-card update.

Tests must be deterministic and offline. Mock external downloads and use `tmp_path`
for storage. Never use an owner's database as a fixture. Do not replace automatic
memory with demonstration ratings. Do not bypass CORS/XSRF or expose local profiles.

Maintainers review code and CI before merging; there is no automatic merge policy.
For vulnerabilities use [SECURITY.md](SECURITY.md), rather than a public bug report.
MIT covers project code; external datasets and artwork retain their own licenses.

Українською: створюйте невеликі PR із поясненням проблеми й перевірок. Для тестів
використовуйте синтетичні дані та тимчасову базу. Не комітьте особисті профілі,
секрети чи завантажені каталоги. Зміни ML потребують окремого відтворюваного
експерименту; історичні цифри не є оцінкою живого застосунку.
