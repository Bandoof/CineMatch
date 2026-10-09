# Security policy / Політика безпеки

## Supported code

Security fixes target the current `main` branch. Older snapshots are not separately
maintained. This is a local Streamlit application, not an authenticated multi-user
service. A clean automated scan is not a security certification.

## Report a vulnerability privately

Use GitHub's **Security → Advisories → Report a vulnerability**, when the repository
owner has enabled private vulnerability reporting. Include the affected commit,
minimal synthetic reproduction, impact and suggested mitigation. Do not include
real profiles or secrets. The owner must enable reporting as described in
[GitHub maintenance](docs/github-maintenance.md); this policy does not assert that
it is enabled. If that button is absent, open an issue requesting a private reporting
channel **without** publishing exploit details or sensitive information. No response
SLA or unattended email inbox is promised.

## Security boundaries

- JSON imports have a byte limit, schema validation and bounded item lists.
- External image/source URLs are allowlisted HTTPS URLs; displayed external text
  is escaped or rendered through Streamlit text components.
- SQLite uses parameterized SQL, local storage and optimistic autosave revisions.
  Named profiles and installation memory share one installation; they are not accounts.
- Default launch/Compose binds localhost. CORS/XSRF stay enabled, static serving
  disabled, and uploads limited. Do not publish a personal installation to the Internet.
- Shared hosting would require a separate design. Disabling local profile storage
  alone does not supply authentication, authorization, rate limits or tenant isolation.
- Local model/catalog files are trusted installation inputs, not supported uploads.
  Dependency auditing and CodeQL complement code review; they do not constitute a pentest.

Українською: повідомляйте про вразливості приватно через GitHub, якщо власник
увімкнув цю можливість. Не публікуйте експлойти, секрети чи профілі у звичайних
issues. Застосунок призначено для локального використання; SQLite не ізолює
користувачів публічного сервісу. Межі перевірок: [security review](docs/security-review.md).
