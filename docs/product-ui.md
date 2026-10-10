# Consumer interface / Новий інтерфейс

The default `streamlit run app/streamlit_app.py` opens the v1.3 consumer surface.
Seven native navigation choices render **only the active page**. Dark slate,
warm amber, bounded three-column poster cards and native responsive stacking
provide CineMatch's own visual identity. CSS in `app/product.css` styles only
our public `st-key-*` container classes and standard elements. Keyboard focus
is visible; reduced-motion preferences are respected. No arbitrary HTML, scripts
or private Streamlit DOM selectors are used by this surface.

Українська та англійська доступні в перемикачі мови. Пошук враховує обидві
мови незалежно від мови інтерфейсу. Деталі показують лише доступні поля джерела,
назву оригіналу, опис із мовним fallback, реальну оцінку та посилання на джерело.
Відсутні постери мають нейтральну заглушку; постери можна вимкнути для роботи
без інтернету. Немає вигаданих описів, оцінок чи дат перегляду.

## State and compatibility / Стан і сумісність

Watchlist, watched, personal stars, not-interested, session snooze and Undo use
explicit reversible transitions. Opening details never marks a title watched.
Autosave keeps the existing SQLite compare-and-swap protection and saves before
Streamlit reruns. Named profiles and JSON backups remain available in My Library.

Schemas 2–5 and legacy rating dictionaries still import. Exports stay schema 5
unless a saved interaction needs a modern provider identity; only then schema 6
adds minimal validated `catalog_refs`. These contain provider/type/names/date/genres,
**no credentials, artwork, ratings, descriptions or viewing history**. Import
stages identities and validates all profile fields before adopting them. No SQLite
migration or destructive rewrite is required. Missing metadata restores an
explicit identity-only title; details can refresh it. Older CineMatch versions
cannot import schema 6; retain your original exports when rolling back.

Експорт без нових provider IDs залишається у форматі 5. Формат 6 відновлює
сучасні назви без кешу, але не вигадує повних метаданих. Пошкоджений профіль
не змінює поточну бібліотеку або каталог. Розділ «Оновлено в цій сесії» показує
лише реальні поточні дії (до 100); ці дати не експортуються і не видаються за
історію попередніх сесій. Snooze та Undo також є станом поточної сесії.

For You keeps the original Adaptive algorithm for known titles. New provider
titles use separately disclosed signed genre affinity and available provider
quality, without collaborative predictions or model retraining. Discovery
definitions are in [discovery-search.md](discovery-search.md). Research controls
are confined to Research, which states the v1.2 evidence limitations.

## Classic compatibility / Classic-сумісність

Set `CINEMATCH_UI=classic` to open the retained v1.2 surface. Existing classic UI
regression tests explicitly select that mode; `tests/test_product_ui.py` removes
the override and tests the real default entry point. Classic can read historical
profiles and models, but requires the historical dataset and does not restore
schema-6 provider identities. To avoid opening a modern autosave with an older
surface, use a **separate** `CINEMATCH_PROFILE_DB` or disable autosave; rejected
profiles preserve their stored data.

Усі профілі — локальні для цієї інсталяції. Це не ізольовані облікові записи
багатокористувацького сервісу. Публічне розгортання не входить у цю зміну.
