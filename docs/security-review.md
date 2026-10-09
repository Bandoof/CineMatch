# Review and security fixes — 9 October 2026

Source review based on main `bd82b4e`, with synthetic fixtures only. No personal
profiles, owner's Windows server, public deployment or external attack target was used.

## Correctness fixes

- A changed title/IMDb identity invalidates cached translations, pages, images
  and completion flags before fetching replacement metadata. A changed source
  page also invalidates the cached description, even when the title is unchanged.
- Wikipedia API soft errors (including maxlag) do not mark descriptions or images
  complete. Normalized page names map back to requested titles. Unmatched responses
  remain retryable; successful responses with no description remain valid absences.
- Rating edits/deletions and restoring watched titles capture the immediately
  previous profile for ML Lab's before/after comparison.
- Missing media/source cells are filled with catalog defaults, so exported
  profiles do not contain accidental NaN metadata.

## Security fixes

- Streamlit 1.41.1 replaced with 1.54.0. This fixes the Windows component-handler
  SSRF / NTLM credential exposure advisory
  [GHSA-7p48-42j8-8846](https://github.com/streamlit/streamlit/security/advisories/GHSA-7p48-42j8-8846).
  The advisory's exposure scenario requires access to the affected endpoints;
  this is not evidence that the owner's local server was attacked.
- Pillow explicitly pinned to 12.3.0 and pytest to 9.0.3 after dependency audit
  flagged their previously installed versions. Many Pillow advisories concern
  formats/functions not exposed by this app's JSON-only upload flow. Updating
  removes known vulnerable installed versions without claiming exploitability.
- `.streamlit/secrets.toml` and environment files are excluded from Docker build
  context and Git. Git ignore rules alone do not exclude files from `COPY . .`.
- The default server listens on loopback. CORS/XSRF protections are explicitly
  enabled, static file serving is disabled, and the existing 1 MB upload limit remains.
  Docker's internal bind is overridden by its command; Compose publishes to loopback.
- Profile parsing rejects duplicate keys, NaN/Infinity and excessive nesting with
  a validation error, before replacing the current profile.
- Presentation, description and TVmaze links share strict HTTPS host validation:
  credentials, control characters, backslashes, invalid ports and nonstandard ports
  are rejected. These are browser links, not an app feature for fetching user URLs.
- CI now audits resolved runtime/development requirements with pip-audit.

## Verification

- Linux / Python 3.11.17: 77 tests passed; Ruff passed.
- Linux / Python 3.10.22: 77 tests passed; Ruff passed, including a fresh dependency install.
- Fourteen warnings are dependency deprecations in Matplotlib/Pyparsing.
- pip-audit 2.10.1: no known vulnerabilities in the checked installed Python 3.11
  environment or separately resolved `requirements-dev.txt` (including runtime dependencies).
- Streamlit startup smoke check: loopback HTTP health returned 200 `ok` with local
  profile storage disabled. Config confirmed CORS/XSRF, upload limit and disabled static serving.
- Tracked files had no matches for the checked private-key, GitHub-token or AWS-key patterns.
  This narrow pattern scan is not proof that every possible secret is absent.
- New regression cases cover cache identity changes, retry after Wikipedia soft
  errors, normalized titles, latest-action snapshots, hostile URLs and malformed profiles.

## Remaining boundaries

This is code review, dependency audit and automated local verification, not a
complete penetration test. Windows exploit reproduction, Docker build execution,
production TLS, reverse-proxy configuration, rate limits and real-user access
control were not tested here. Docker is unavailable in this workspace.

Local SQLite is still one installation's shared memory, without account
authentication. For any shared hosting, set `CINEMATCH_LOCAL_PROFILES=0`; private
multi-user storage requires a separate authenticated design. Do not expose the
personal local installation publicly. Existing data and saved profiles were not migrated.

The MovieLens benchmark and model-quality claims were not changed or rerun.

## v1.1 targeted follow-up — 9 October 2026

Profile transitions were extracted without moving persistence into the UI. Autosave
JSON now uses the same bounded parser as imports (with the existing 20 KB envelope
allowance); duplicate keys, non-finite constants and excessive nesting raise a
controlled ValueError. Tests prove corrupt rows are preserved and rollback/stale
writers do not overwrite committed data. This is local corruption resilience, not
an assertion of remotely exploitable SQLite access.

Revisited parameterized SQL, URL/HTML handling, explicit ZIP-member allowlists and
size limits, numerical `allow_pickle=False` models, environment/Docker exclusions,
workflow permissions and cache copies. No new confirmed vulnerability was found in
these reviewed paths beyond the autosave parsing weakness. Source/model files remain
trusted local inputs; there is no public multi-user authorization or request-rate
limiting. The engine and score caches are bounded by entry count, not a memory quota.

Actions are pinned; Python CodeQL and dependency auditing are automated. A successful
CodeQL run alone does not certify absence of findings. Repository administrative
settings remain owner actions. No deployed-site pentest or private-data access was
performed. [Engineering evidence](engineering-v11.md) separates local and CI results.
