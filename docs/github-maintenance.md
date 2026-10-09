# Owner settings / Налаштування власника

Workflow files configure checks, not repository administration. The following
settings have **not** been enabled or verified by this change. Check them as owner
in `Bandoof/CineMatch` after reviewing the PRs.

1. **Settings → Rules → Rulesets → New branch ruleset**: target `main`, require a
   pull request and resolved conversations; block force pushes/deletion. After the
   new workflows have actually run, select their existing test/security/CodeQL
   status checks as required checks. Require one approving review only if a second
   reviewer is available; do not make a solo-maintainer repository impossible to merge.
2. **Settings → Security → Advanced Security** (the label may appear as Code security):
   enable dependency graph, Dependabot alerts/security updates, secret scanning and
   push protection where available. The YAML config only proposes version updates.
3. In the same security settings, enable **Private vulnerability reporting**. Verify
   that **Security → Advisories → Report a vulnerability** is available to reporters.
4. **Security → Code scanning**: review the Python workflow run and alerts. If default
   setup was enabled, switch to advanced setup for the committed CodeQL workflow;
   avoid running both setups. Investigate failed uploads rather than marking them green.
5. **Settings → Actions → General**: retain read-only workflow token defaults. Review
   third-party/fork workflow approvals. CodeQL alone needs `security-events: write`.
6. Review Dependabot PRs and newly reported advisories. Never automate updates into
   `main` solely because tests pass. Confirm badges show actual default-branch runs.

Documentation: [private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository),
[Dependabot configuration](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-version-updates),
[CodeQL advanced workflow](https://docs.github.com/en/code-security/reference/code-scanning/workflow-configuration-options).

Українською: ці адміністративні перемикачі має перевірити власник. Наявність YAML
не доводить, що захист `main`, приватні звіти або secret scanning уже ввімкнені.
