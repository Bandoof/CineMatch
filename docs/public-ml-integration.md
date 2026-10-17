# CineMatch v1.5.0 — Public ML Integration

Стан: підготовка PR до main, без публікації пакета, деплою чи релізу.
База: v1.4.2 / `7d3a6528331500c58d2b118d2ac760536605caa9`.

## Рішення та перевірені джерела (17.10.2026)

Старий `scripts.prepare_portfolio` змішував MovieLens 100K і latest-small.
[README 100K](https://files.grouplens.org/datasets/movielens/ml-100k/README)
забороняє перерозповсюдження без окремого дозволу. Тому такий пак не підходить
для публічного Git, Release, CDN або загальнодоступних CI artifacts.

[README latest-small](https://files.grouplens.org/datasets/movielens/ml-latest-small-README.html)
дозволяє поширення набору та перетворень на тих самих умовах. Потрібні
атрибуція, відсутність заяв про схвалення GroupLens і окремий дозвіл для
комерційного або прибуткового використання. MIT-ліцензія коду ці умови не замінює.
Пак містить повний оригінальний README; модель також не оголошується MIT-даними.
Атрибуція: F. Maxwell Harper and Joseph A. Konstan (2015), The MovieLens Datasets:
History and Context, DOI: https://doi.org/10.1145/2827872.
Це development snapshot, не доказ якості на незалежному benchmark/holdout.

## Мінімальна реалізація

- Завантажити лише офіційний `https://files.grouplens.org/datasets/movielens/ml-latest-small.zip`;
  SHA-256 `696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436`.
- Використати наявний адаптер `extend_movies` з порожньою базою 100K:
  namespace фільмів/користувачів latest-small зберігається; дані 100K не читаються.
- Вибрати до 250 назв за кількістю публічних оцінок, додавши точні IMDb-збіги
  прикладного каталогу; залишити до 30 000 реальних подій. Не додавати синтетичні
  взаємодії до навчання. Для детермінованого вибору збережено чинне сортування.
- Навчити окремий BiasedMF зі звичайними параметрами (24 factors, 15 epochs,
  regularization 5, bias_regularization 5, random_state 42), потім зберегти NPZ.
  Обчислення ALS, Item-KNN, content, hybrid і ranking не змінені.
- `prepared_engine` приймає лише schema 2 з відомим джерелом, SHA-256 файлів,
  обмеженнями кількості/розміру, дозволеними колонками, числовими оцінками та
  перевіркою форми/скінченності моделі. Legacy schema 1 відхиляється.
  Відсутній або некоректний пак залишає metadata fallback; для помилки є попередження.
- Collaborative початково вибраний лише в portfolio UI. Нова оцінка знайомого
  фільму змінює fold-in користувача без перенавчання item factors. Порожній профіль
  або профіль лише з невідомими моделі назвами отримує популярність із поясненням.
- Adaptive без навченої політики лишається community-quality fallback;
  Semantic без текстової моделі — жанровий fallback. Нові фільми/серіали — окремі
  жанрові евристики. Ці режими не видаються за виміряне покращення ML.
- Прикладні оцінки задано через IMDb, щоб старі ID 100K не змінили значення.

## Контракт пакета

| Файл | Вміст | Ліміт читання |
|---|---|---:|
| manifest.json | schema 2, archive hash, file hashes, counts, scope | 5 KB |
| dataset.json | movies + ratings | 8 MB; 250 / 30 000 rows |
| model.npz | numeric arrays, training fingerprint, defaults | 20 MB compressed/decompressed |
| MOVIELENS-LICENSE.txt | повний README latest-small, умови й citation | 50 KB |

У ratings лише user_id, movie_id, rating, timestamp з публічного snapshot.
Ідентифікатори тут псевдонімні, а не приватні акаунти відвідувачів. Демографії,
вільних тегів, SQLite, токенів, owner profiles, дослідницьких ваг чи holdout немає.
Контрольні суми в manifest перевіряють цілісність; самостійно вони не засвідчують
походження довільного файла. Довіряти треба лише пакету, зібраному цим скриптом
у контрольованому середовищі; не приймати пакети від відвідувачів.

## Підготовка й перевірка локально

```bash
OPENBLAS_NUM_THREADS=1 python -m scripts.prepare_portfolio --directory data/portfolio
CINEMATCH_TEST_PUBLIC_PACK=data/portfolio python -m pytest tests/test_portfolio.py -q
CINEMATCH_PORTFOLIO_DATA_DIR=data/portfolio python -m streamlit run app/portfolio_app.py
```

У PowerShell встановіть змінні окремо через `$env:NAME="value"`.
Наявний destination не перезаписується. Новий пак спочатку перевіряється в staging,
потім атомарно перейменовується; вихідні CSV автоматично видаляються зі staging.
Для оновлення оберіть новий каталог і після перевірки змініть шлях оператора.
`data/` ігнорується Git. Приватні локальні джерела не використовуються.

## Пропозиція розміщення — лише після окремого підтвердження

Найменше рухомих частин для цього невеликого пакета: після затвердження умов і
конкретних hashes додати тільки чотири перевірені файли в versioned deployment
checkout (наприклад `assets/public-ml/v1/`), доступний Community Cloud. Призначити
`CINEMATCH_PORTFOLIO_DATA_DIR=assets/public-ml/v1` для dedicated portfolio entry point.
Зберегти весь README й умови поруч із даними; не додавати профілі або secrets.
Не потрібні LFS, нова залежність, довільний remote URL чи навчання при старті сесії.
У цьому PR файли пакета залишаються локальними: merge сам по собі ML у чинному
публічному демо не ввімкне. Публікація пакета/зміна hosting configuration — окремий
перевірюваний крок після дозволу. Альтернатива для власного сервера — read-only
mount готового каталогу. Не покладатися на збереження тимчасових файлів хмари.

[Streamlit status/limitations](https://docs.streamlit.io/deploy/streamlit-community-cloud/status)
і [resource guidance](https://docs.streamlit.io/knowledge-base/deploy/resource-limits)
описують спільні ресурси та способи обмеження пам’яті. Не трактувати старі форумні
цифри RAM/CPU як гарантовану поточну квоту. Community Cloud працює на Linux;
перевірити версію Python і залежності, відносні шляхи, reboot/hibernation та фактичні
ресурси конкретного застосунку перед активацією. Навчання офлайн; на кожну сесію
окремі engine/profile/LRU, без shared cache_resource з приватними ключами профілю.
Обмеження розміру пакета не є гарантією допустимої кількості одночасних відвідувачів.
Постери TVmaze лишаються необов’язковими з чинним повідомленням про мережеві дані.

## Перевірки

Контрактні тести використовують явно синтетичну fixture. Окремий opt-in тест із
`CINEMATCH_TEST_PUBLIC_PACK` перевіряє справжній підготовлений пак через два AppTest:
оцінка в UI змінює Collaborative, результат збігається з незмінним Recommender,
друга сесія незмінна, reset повертає приклад, приватне сховище/provider client не
створюються. CI browser job готує реальний latest-small пак і запускає цей тест
до desktop/mobile browser journeys. Пак не включено до uploaded QA artifacts.

Метрики якості, latency у production, SLA й новий holdout не заявляються.
