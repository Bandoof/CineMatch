# CineMatch: engineering case study / Інженерний кейс

## Problem and purpose / Проблема й мета

Movie discovery combines two different problems: finding real, correctly
identified titles and choosing among films a model actually knows. CineMatch
explores both without treating recent metadata as fabricated training history.
Its portfolio goal is to make recommender engineering understandable in a
three-to-five-minute demonstration, with a useful bilingual local application.

Пошук актуальних назв і рекомендації на історичних оцінках — різні задачі.
CineMatch показує їхній зв’язок і межі: реальні метадані, прозорі алгоритми,
український пошук, оцінювання й бібліотека без обов’язкового акаунта.

## Data and models / Дані та моделі

MovieLens 100K/latest-small are explicit public **development** sources. Original
algorithms remain Adaptive, Semantic, Hybrid, Collaborative (biased matrix
factorization), Item-KNN, Content-based and Popularity. TF-IDF/LSA and cached
MiniLM are optional research artifacts, not mandatory downloads. Missing text
models and learned mixing policies are labeled as fallbacks. New films/series
use separate genre/provider-quality heuristics, not unseen-item collaborative
predictions or invented popularity.

The credential-free fixture has 22 real films and eight TVmaze series; all 30
have source-linked Ukrainian labels, 25 have Ukrainian short descriptions, 19
have release years from 2023. Wikidata CC0 labels are not machine translations.
TVmaze remains the series provider; optional TMDB remains available in local
mode. No token was available, so live TMDB success is **not** claimed.

Навчальні дані не підмінено сучасним каталогом. Добірка з 30 назв невелика й
датована; це не оцінка покриття всього світового кінематографа. Опис Wikidata
позначено як короткий фактографічний опис, а не згенерований сюжет.

## Decisions and challenges / Рішення й складнощі

- Preserve Streamlit and the numerical architecture. A catalog facade adds
  stable namespaces, exact IMDb/type/year joins and provenance around the engine.
  Ambiguous release dates are withheld; source years remain useful.
- Preserve local SQLite/CAS and schemas 2–6. A dedicated portfolio entry avoids
  local profile stores, imports and provider credentials entirely.
- Seed clearly synthetic preferences on real identities. Reset and refresh
  restore the example; independent sessions own their engines, indexes and LRUs.
- Discover defects through execution: Windows changed snapshot line endings,
  stale nested Docker bytecode broke source inspection, native Streamlit 1.54
  ARIA attributes failed axe, and pagination step buttons lacked names. Specific
  source/packaging/framework changes resolved them without changing score assertions.
- Keep offline usage honest: metadata works locally; remote artwork is optional.
  Shareable v1.4 screenshots disable third-party posters.

Основний компроміс: окремий невеликий public pack потрібен для показу справжньої
матричної факторизації. Без нього застосунок чесно демонструє лише метадані й
жанрові евристики. Це кращий технічний доказ, ніж удавані ML-прогнози для нових назв.

## Measured evidence / Вимірювання

Exact integrated v1.3 main was verified before v1.4. The same synthetic fixture
keeps the original recommendation output hash. Current v1.3 → v1.4 cold startup
393.87 → 410.73 ms and warm rerun 14.99 → 20.47 ms show a small regression after
the accessibility/framework changes; they are not claimed as an optimization.
Historical v1.3 facade 2625.68 → 265.43 ms used 11,096 titles and is preserved as
historical evidence, not compared to the smaller demo. Five retained public-pack
engines peak around 122 MiB in a Linux service process; global profile-cache
growth is zero. This is not load testing, an SLA or a statistical quality gain.

233 local tests pass with cached optional CPU weights; Docker/default CI skip
the two explicitly optional integrations. Real desktop/mobile/tablet browser
flows cover rating, Undo, filters, languages, reset, refresh and two visitors.
Automated accessibility has no violations on audited views but one incomplete
ARIA finding needs manual review. See [QA evidence](qa-v14.md),
[architecture](architecture-v14.md) and [demo threat model](portfolio-demo.md).

## Limits, learning and future research / Межі й наступні кроки

The historical **+17.8% Adaptive claim remains unverified**. The 326-user v1.2
final cohort has already been consumed; no new final holdout was executed.
Metadata coverage, synthetic speed, and interface tests do not validate ML
ranking quality. A future study needs a newly registered protocol, untouched
data/cohort and clear confidence intervals before changing production policy.

Lessons: identity and evidence provenance matter as much as algorithms; a cache
that holds profiles must respect session boundaries; offline/error states are
part of the product; a green unit suite does not prove browser accessibility.
Before public hosting, manually review accessibility, platform resource limits,
data/artwork terms and the exact deployed entry/configuration.

v1.4 changes were prepared with AI-assisted engineering and remain subject to
owner review. A portfolio candidate should review, understand and describe their
actual contribution; this case study does not claim individual authorship of
unreviewed AI-generated changes. No public deployment or Release was created.

Українською: цінність кейсу — у відтворюваних рішеннях, чесних обмеженнях і
перевірених сценаріях. Наступні дослідження потребують нових невикористаних даних;
ані гарний інтерфейс, ані швидкий benchmark не доводять приріст якості рекомендацій.
