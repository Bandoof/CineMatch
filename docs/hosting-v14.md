# Hosting decision / Вибір хостингу

**No public deployment exists or is authorized.** Recommendation: start with
Streamlit Community Cloud using the dedicated portfolio entry and the shipped
metadata-only fixture; show the complete ML pack locally or in the recorded demo
until an immutable hosted pack and its redistribution terms have been reviewed.
Accounts, platform setup and a public URL require owner approval.

Official documentation read on **2026-10-10**:
[Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud),
[app settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings),
[HF Spaces overview](https://huggingface.co/docs/hub/spaces-overview),
[HF storage](https://huggingface.co/docs/hub/spaces-storage),
[Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker),
[Render free services](https://render.com/docs/free).
Plans can change; the observations below are not a price or capacity guarantee.

| Option | Compatibility and cost | Memory / cold starts | Storage / setup / maintenance |
|---|---|---|---|
| Streamlit Community Cloud | Native Python/Streamlit; official docs describe free app hosting. Best initial zero-cost fit. | A fixed numeric free memory guarantee was not verified in the inspected pages. Test the exact app against account limits; idle/rebuild startup is possible. | Treat writable disk as disposable. Owner GitHub/account connection and dedicated entry/config required; low maintenance. Do not persist visitor SQLite. |
| Hugging Face Docker Spaces | Compatible Docker runtime. Current docs say **creating Docker/Gradio compute Spaces requires a paid PRO/Team/Enterprise plan**, despite CPU Basic having no hourly hardware charge. Not universally zero-cost. | CPU Basic: 2 vCPU, 16 GB RAM; free hardware sleeps when unused. | Default 50 GB disk is nonpersistent; explicit Docker port/user configuration and build needed. Owner account/plan required; moderate maintenance. |
| Render free web service | Python or Docker with WebSocket support; official free web-service tier. Alternative if Community Cloud limits are unsuitable. | Spins down after 15 idle minutes; 750 free instance hours per workspace/month. Exact current memory tier was not verified here. | Ephemeral files disappear on restart/redeploy/spin-down; no persistent disk on free web services. Owner account, explicit entry/port/build needed; moderate maintenance. |
| Local interview / recorded demo | Full existing ML architecture, no hosting fee or visitor accounts. | Measured on this Linux environment; Windows CI is separate. | Own machine, session-isolated portfolio entry, public pack explicitly prepared. No public service or remote access needed. |

Visitors need no account in the proposed app; **operators** need platform
accounts. Do not make a private local-profile application public. Use only
`app/portfolio_app.py`, a clean checkout/image and immutable public metadata.
The default Docker target remains local; the public candidate target is explicitly
`docker build --target portfolio`. No port has been published in this task.

## Approval checklist for a concrete deployment

1. Owner reviews and merges v1.4 PRs in order. Choose an exact reviewed commit;
   do not point a public service at a changing unreviewed branch.
2. Inspect the platform's current terms, capacity, cost and security controls.
   Start without TMDB credentials, private files, writable named profiles or
   shared SQLite. Do not copy a developer `.env`, secrets file, `data/` or `models/`.
3. Use the dedicated entry, `CINEMATCH_MODE=portfolio` if an environment selector
   is also configured, disabled static serving, normal TLS/XSRF protection and
   usage telemetry off. Never expose a developer terminal or remote filesystem.
4. For a full ML public demo, prepare/validate a bounded pack from pinned official
   public archives in an isolated build. Review GroupLens redistribution terms
   first; do not upload an owner's database or history. Metadata-only operation
   is explicit and honest if a pack is unavailable.
5. Re-run two-browser isolation/reset/error tests on the **exact hosted instance**
   before sharing it. Current isolation evidence is local and CI, not a hosted
   platform certification. Apply platform memory/CPU/concurrency/egress budgets;
   application item/event caps are not visitor-admission or DoS protection.
6. Show the session/privacy notice. Prefer posters disabled initially: enabled
   artwork causes browser requests to TVmaze. Recheck provider/data/artwork
   terms, attribution and any redistribution of screenshots/video.
7. Obtain explicit owner approval for the final concrete public configuration
   and URL. Do not automatically deploy from these documents or create a Release.

Українською: базовий вибір — Community Cloud для безкоштовного невеликого показу
метаданих. Повний ML-показ уже доступний локально з окремим public pack. Docker
Spaces сумісний, але за актуальними правилами його створення потребує платного
плану. Render має безкоштовний режим зі сном і тимчасовими файлами. Жодна
платформа не робить спільний SQLite безпечним: використовуйте лише ізольований
деморежим. Розгортання та публічне поширення потребують окремого дозволу власника.
