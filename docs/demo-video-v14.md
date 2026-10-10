# Four-minute portfolio presentation / Чотирихвилинний показ

Status: a storyboard, bilingual narration/captions and **real silent QA footage**
are supplied. A finished narrated 3–5-minute video has **not** been recorded or
published. See [media provenance](../assets/v14/README.md). Do not describe the
short QA clip as the complete presentation.

## Prepare / Підготовка

Use the reviewed candidate locally with `app/portfolio_app.py`. Prepare the
separate public pack first (`python -m scripts.prepare_portfolio --directory
data/portfolio`) for real Collaborative recommendations. Verify the explicit
ML-pack notice; if it is absent, describe metadata heuristics only and omit the
ML prediction scene. Reset the example, select Ukrainian or English, disable
posters in **Your demo session / Ваша демосесія** and collapse the controls.
No private local profile, token, terminal environment or personal watch history
should appear. All example preferences are visibly synthetic.

OBS or equivalent: 1920×1080 capture, 30 fps, H.264, readable 100% browser zoom,
visible cursor, microphone 48 kHz, no music/film audio. Keep captions away from
buttons. The supplied QA capture is 1280×720; it is not a claimed 1080p recording.
Rehearse click order before recording; pause when Streamlit finishes rerunning.
Record Ukrainian and English separately, using their respective scripts below.
SRT files contain concise captions; align them to the final recording before
publishing. No upload or publication is authorized by these documents.

## Storyboard and exact clicks / Сцени й натискання

| Time | Screen / Action | Point to explain |
|---|---|---|
| 00:00–00:20 | Open portfolio entry; show demo banner and Discover. | Bilingual, local-first project; example ratings, real title data. |
| 00:20–00:40 | Scroll to Portfolio selection; open a recent film/series card. | Small dated collection, not a fabricated trending chart. |
| 00:40–01:00 | Back → Search; enter `Інтерстеллар 2014` / `Interstellar 2014`, Enter. | Ukrainian source title and year disambiguation. |
| 01:00–01:20 | Expand Filters & sorting; try Series, then Movies. Open Details. | Useful no-result explanation, exact media filter and source links. |
| 01:20–01:40 | Read title/source; change familiar Interstellar rating from 4.5 to 4; Save rating. | Synthetic preference changes, not invented provider ratings. |
| 01:40–02:00 | For You → Recommendation algorithm → Collaborative. Scroll to known-film cards. | Actual biased matrix factorization on a separate public development subset. |
| 02:00–02:20 | Briefly show algorithm selector and a reason; scroll to New possibilities. | Seven original modes; default Adaptive/text fallbacks; modern titles are heuristics. |
| 02:20–02:40 | Search `Пуститися берега` / `Breaking Bad`; Details → Watchlist. | One intentional state change; explicit source metadata. |
| 02:40–03:00 | My Library; Your demo session → Undo; repeat Watchlist if needed. | Rating/watched/watchlist distinction and reversible actions. |
| 03:00–03:20 | Switch language to English/Ukrainian and back; briefly resize narrow viewport. | Preserved selections and responsive native controls. |
| 03:20–03:40 | Research; show unverified +17.8% warning and archived evidence. | Engineering tests do not validate ML quality; consumed final cohort. |
| 03:40–04:00 | Reset example; optional empty profile then reset; finish on Discover. | Visitor isolation, no account/shared SQLite; owner review/deployment approval pending. |

Allow 10–20 seconds extra for questions/loading and stay within five minutes.
There is no public demo URL to show. Refer viewers to GitHub and local setup.

## Ukrainian narration / Український текст

**00:00.** Це CineMatch — локальний застосунок для пошуку фільмів і серіалів,
створений на Python та Streamlit. Тут я показую окремий демонстраційний режим.
Назви й метадані справжні, а оцінки профілю навмисно синтетичні: це не чиясь
особиста історія переглядів.

**00:20.** На головній сторінці є пояснені добірки. Цей приклад містить
двадцять два фільми й вісім серіалів. Це невеликий датований каталог із посиланнями
на джерела, а не вигаданий рейтинг популярності. Він працює без API-ключа.

**00:40.** Знайду «Інтерстеллар» українською та додам рік. Індексований пошук
поєднує оригінальну й доступну локалізовану назву, підтримує частковий запит і
транслітерацію. Рік допомагає відрізняти однойменні твори й перевидання.

**01:00.** Фільтри відокремлюють фільми від серіалів, жанри та роки. Якщо
обраний тип не відповідає запиту, інтерфейс пояснює порожній результат. На сторінці
деталей можна перевірити джерело української назви. Невідомі поля залишаються
невідомими; переклади й оцінки не генеруються.

**01:20.** Зміню оцінку знайомого фільму й підтверджу її кнопкою форми.
Вона належить лише цьому прикладу. Оцінювання, переглянутий стан і список
«дивитися пізніше» — різні дії. Відкриття деталей саме по собі не означає,
що користувач уже подивився фільм.

**01:40.** Для відомих історичних фільмів виберу Collaborative. Тут працює
наявна матрична факторизація на окремому обмеженому публічному development-наборі.
Модель використовує оцінки, щоб обчислити рекомендації. Це демонстрація механізму,
а не новий експеримент із доведеним приростом якості.

**02:00.** Доступні сім наявних режимів. Adaptive без навченої політики
чесно показує резерв за якістю спільноти; без текстового артефакту Semantic
використовує жанровий резерв. Нові назви нижче підбираються окремими метаданими
й жанровими евристиками, а не удаваними collaborative-прогнозами.

**02:20.** Додам «Пуститися берега» до списку перегляду. Назва походить із
перевірюваного джерела, а ідентичність зберігається в просторі TVmaze.
Каталог узгоджує дублікати лише за унікальним IMDb, типом і роком, щоб не
змішувати різні твори за схожою назвою.

**02:40.** У бібліотеці видно вибрані назви й оцінки. Скасування повертає
попередній стан. У звичайному локальному режимі є SQLite та JSON-резервні копії;
ця демонстрація натомість не відкриває приватні збережені профілі й не записує
спільну базу для відвідувачів.

**03:00.** Інтерфейс можна перемкнути між українською та англійською.
Вибрані фільтри зберігаються; на вузькому екрані картки складаються вертикально.
Браузерні перевірки охопили desktop, mobile і tablet, але ручна перевірка
screen reader та реальних пристроїв ще потрібна.

**03:20.** У дослідницькому розділі збережено методологію й історичні
обмеження. Твердження про плюс сімнадцять цілих вісім десятих відсотка залишається
непідтвердженим. Уже використаний final cohort не запускався повторно. Тести
інтерфейсу та швидкості не замінюють незалежного оцінювання рекомендацій.

**03:40.** Відновлю приклад. Зміни ізольовані в поточній сесії; оновлення
сторінки також повертає початковий стан. Публічного розгортання наразі немає.
Мета проєкту — показати корисний продукт, зрозумілу ML-архітектуру й чесні докази.
Перед релізом власник має переглянути зміни та матеріали.

## English narration

**00:00.** This is CineMatch, a local movie and series discovery application
built with Python and Streamlit. I am using its dedicated portfolio demonstration.
The titles and metadata are real; the profile preferences are deliberately
synthetic. No person's private viewing history is being shown.

**00:20.** Discovery offers collections with clear explanations. This example
contains twenty-two films and eight series, captured as a small dated selection
with traceable source links. It is not a fabricated popularity chart or a complete
modern catalog, and it works without an API key.

**00:40.** I will search for Interstellar and specify its release year.
The indexed search combines original and available Ukrainian titles, partial
matching and transliteration. A year helps distinguish works with the same name.
Ukrainian labels come from real source records rather than generated translations.

**01:00.** Filters separate movies and series, genres and years. A conflicting
media filter gives a useful empty result. The details page links back to the
source title information. Missing fields stay missing: the application does not
invent plots, community ratings or precise release dates.

**01:20.** I will change a familiar film's example rating and submit the form.
Ratings, watched state and watchlist membership are separate actions. Merely
opening a detail page does not mark the title watched. This preference changes
only my demonstration session and can be reset without touching a real profile.

**01:40.** For historical titles I will select Collaborative. This runs the
existing biased matrix factorization using a separate bounded public development
subset. The preferences feed actual numerical recommendations. This demonstrates
how the engine works; it is not a new holdout evaluation or a validated quality gain.

**02:00.** Seven original modes are available. Without a learned policy,
Adaptive discloses its community-quality fallback for films. Without text artifacts,
Semantic falls back to genres. The modern titles below use separately explained
metadata heuristics. They are not collaborative predictions for unseen training items.

**02:20.** I will add Breaking Bad to the watchlist. Its metadata and identity
come from TVmaze, with the Ukrainian label linked to its source. Cross-provider
deduplication requires a unique IMDb identifier, matching type and year.
Similar names alone are not enough to merge two works.

**02:40.** My Library separates saved titles, ratings and watched state.
Undo restores the previous action. The ordinary local application supports SQLite
and JSON backups. This portfolio entry instead avoids private profile stores
and shared visitor persistence, so it cannot overwrite an owner's existing profile.

**03:00.** The interface switches between Ukrainian and English while preserving
filter selections. Cards stack on a narrow screen. Real browser tests cover
desktop, mobile and tablet, but automated accessibility checks are not certification.
Manual screen-reader and actual device testing remain part of owner review.

**03:20.** Research shows the original evidence and its limitations. The historical
seventeen-point-eight-percent Adaptive improvement remains unverified. The consumed
final cohort was not rerun. Functional tests, metadata coverage and engineering
latency measurements do not substitute for independent scientific ranking evaluation.

**03:40.** I will reset the example. Preferences are session-owned and a refresh
also restores the initial state. No public deployment exists yet. The project's
value is a useful product, understandable recommender architecture and reproducible,
honest engineering evidence. The owner still needs to review these assisted changes
before release or claims of individual authorship.

## Owner finish / Що доробити власнику

Review the code and narrative, rehearse the current UI, perform manual accessibility
checks, record/narrate the full four-minute walkthrough, align subtitles, review
the final audio/video and obtain any separate publication/deployment approval.
No completed narrated video, live URL or public upload is claimed.
