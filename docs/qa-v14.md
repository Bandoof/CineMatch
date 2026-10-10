# Portfolio verification / Перевірка портфоліо

Evidence: [`reports/engineering_v14.json`](../reports/engineering_v14.json).
Stage A was completed before v1.4 development; exact v1.3 main is
`40eb03ff0b0d8ecdfad83d22db08eaf5e552db0d`. All four dependent heads were retargeted,
merged from the updated base, reviewed and freshly tested before their authorized
merge commits. Each resulting main passed Linux, Windows, audit and CodeQL.

## Actual results

| Scope | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Final v1.3 local, optional pinned CPU encoder | 220 | 0 | 0 |
| Final v1.3 each CI platform / clean Docker | 218 | 0 | 2 |
| v1.4 local, optional pinned CPU encoder | 233 | 0 | 0 |
| v1.4 network-disabled Docker | 231 | 0 | 2 |

Two skipped default tests require separately supplied MiniLM weights. No test
downloads these weights. Fourteen existing Matplotlib/Pyparsing deprecation
warnings remain. Ruff, expanded import/format checks, configured strict Mypy
(three numerical/state modules), pre-commit and surviving v1.2 evidence hashes
pass. Audits after Streamlit 1.65: 100 requirements / 113 installed dependencies,
zero known vulnerabilities on 2026-10-10; this is not a future security guarantee.

The real Playwright 1.63 / Chromium 153 suite checks desktop 1440×1000, mobile
390×844 and tablet 768×1024, UK/year search, media filters and empty results,
details, rating, watchlist, Undo, library, UK/EN/UK switching, two independent
visitors, empty/reset/fresh-session state, internet-offline metadata and visible
keyboard focus. No JavaScript errors or failed requests in the passing run.
No SQLite file appears at the deliberately configured sentinel path.
AppTest additionally forbids profile-store/provider-client construction and
local-memory initialization, and verifies exact original numerical formulas
with visitor-owned LRU caches. Five retained service sessions do not increase
the original global profile cache.

## Accessibility limits

Pinned axe-core 4.14 checks WCAG A/AA tags on seven settled views. No violations
in the passing run; an ARIA item in For You was classified **incomplete**, not
passed, and requires manual inspection. The initial 1.54 sidebar/combobox ARIA
defects and unlabeled number-input step buttons were detected before changing
the framework/controls. Artwork now has explicit alternative text. Gold keyboard
focus is observed at 3 px. Audit includes rendered contrast; it is not formal
WCAG certification, complete keyboard coverage or screen-reader verification.
Manual checks remain: NVDA/VoiceOver, opened comboboxes, slider announcements,
200% zoom, touch targets and actual mobile hardware. Native framework controls
can still use English accessibility strings within the Ukrainian interface.

## Performance and reproducibility

The same synthetic 1,500-item / 100-user / 2,400-event fixture, eight factors,
three epochs, 20 score repetitions and one BLAS thread produced the unchanged
recommendation SHA256 `9efaf4a62d7ab31c21cf4c93e386532074c645a5564012c3e849b1ef69929679`.
Integrated v1.3 → v1.4: cold AppTest 393.87 → 410.73 ms; warm rerun 14.99 →
20.47 ms. This is a small **regression**, not an improvement, accompanying the
framework/accessibility changes. It remains below historical v1.2 warm 46.43 ms;
the earlier v1.3 16.34 ms is historical, not a guaranteed baseline.

Measured Linux 6.18.44 / Python 3.11.16 / NumPy 1.26.4, managed cgroup quota
two CPU equivalents / 8 GiB memory. Other managed services can contend for CPU;
these are observations, not controlled hardware confidence intervals or SLAs.
10,000-title synthetic search retains 6/6 expected top results. The separate
real public pack contains 222 films, 29,974 canonical latest ratings and 248
combined identities; five retained engines peak at about 122 MiB in the service
process. Do not compare its facade timings to the historical 11,096-item facade
measurement. Browser and Docker health include transport/start overhead and are
separate from synthetic reruns. Neither fixture evaluates ML quality.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pre_commit run --all-files
OPENBLAS_NUM_THREADS=1 python -m scripts.benchmark_performance --repetitions 20 --output work/performance.json
python -m scripts.benchmark_discovery --output work/search.json
python -m scripts.prepare_portfolio --directory data/portfolio
OPENBLAS_NUM_THREADS=1 python -m scripts.benchmark_portfolio --pack data/portfolio --output work/sessions.json
python -m pip install playwright==1.63.0
python -m playwright install chromium
# Start app/portfolio_app.py at localhost:8514 in another terminal.
python -m scripts.verify_portfolio_browser --isolated-demo --output work/browser
```

Create `work/` first. On PowerShell set `$env:OPENBLAS_NUM_THREADS='1'` instead
of a shell prefix. Optional axe is supplied with `--axe-script /path/to/axe.min.js`;
GitHub's pinned browser workflow installs it in a temporary QA directory. Use
`--no-artwork` for shareable captures without redistributing third-party posters.
`--expect-pack-error` checks an explicitly invalid public pack's visible fallback.
Never run browser actions against the owner’s local profile entry point.

No permanent OS trust or CA changes, disabled TLS verification, new scientific
holdouts or rewritten research reports were used. Earlier stale Docker bytecode
was resolved through clean source; recursive Docker exclusions prevent recurrence.
The default Docker build still opens the local app; `--target portfolio` is explicit.
Final GitHub head/check URLs and recovery instructions are in
[`progress-v14.md`](progress-v14.md). v1.4 remains unmerged and undeployed.
