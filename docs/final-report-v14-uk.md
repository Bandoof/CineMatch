# CineMatch: підсумковий звіт v1.3 → кандидат v1.4

Дата: 10 жовтня 2026 року. Stage A завершено до початку Stage B.
v1.4 підготовлено в review PRs; нові PRs не злиті. Публічного розгортання,
версійного тегу та GitHub Release немає. Жодну приватну інфраструктуру не змінено.

## 1–3. Інтеграція v1.3 і точний main

| PR | Статус | Merge commit |
|---|---|---|
| [#16 Modern Catalog](https://github.com/Bandoof/CineMatch/pull/16) | MERGED | `2adde7975b3e353a7dfc1a9445bbf19c00e96405` |
| [#17 Search & Discovery](https://github.com/Bandoof/CineMatch/pull/17) | MERGED | `71594c7c5e34a56afdd4a54847d5638b8d3eef53` |
| [#18 Cinematic UI & Library](https://github.com/Bandoof/CineMatch/pull/18) | MERGED | `d64fb0e1d9ddd53fd5493bd2b55ccecf85679940` |
| [#19 QA, Performance & Documentation](https://github.com/Bandoof/CineMatch/pull/19) | MERGED | `40eb03ff0b0d8ecdfad83d22db08eaf5e552db0d` |

Фінальний v1.3 main: **`40eb03ff0b0d8ecdfad83d22db08eaf5e552db0d`**.
Початкові стани, base/head, commits, mergeability, actual diffs і checks
перевірено через актуальний GitHub. #17–#19 послідовно перенаправлено на main,
оновлено merge із новою базою та протестовано на свіжих heads. Merge commits
створено лише після успішних перевірок; після кожного злиття перевірено main.
Захист/обов’язкові checks не обходилися; force-push main не використовувався.

## 4. CI, безпека й сумісність

| Стан | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Фінальний v1.3 локально з кешованими CPU weights | 220 | 0 | 0 |
| v1.3 кожна CI-платформа / чистий Docker | 218 | 0 | 2 |
| v1.4 локально з кешованими CPU weights | 233 | 0 | 0 |
| v1.4 стандартний CI / Docker | 231 | 0 | 2 |

Два пропуски стосуються явно optional MiniLM інтеграцій без наданих weights;
локально обидва виконані. Залишаються 14 наявних Matplotlib/Pyparsing warnings.
Ruff, imports/format, налаштований strict Mypy для трьох модулів, pre-commit,
dependency audits і CodeQL пройшли. Після оновлення Streamlit перевірено 100
requirements-залежностей і 113 установлених: **0 відомих вразливостей** на дату
перевірки. Це не гарантія відсутності майбутніх CVE.
Final clean-archive Docker спочатку отримав 12 collection errors ENOSPC; без
зміни тестів окремий tmpfs/cache дав 231 passed / 0 failed / 2 skipped.

Main CI: [Linux/Windows/audit](https://github.com/Bandoof/CineMatch/actions/runs/38068700880),
[CodeQL](https://github.com/Bandoof/CineMatch/actions/runs/38068700593).
Результати на точних поточних heads v1.4 доступні в checks відповідних PRs.
Підсумкові вимірювання: [engineering_v14.json](../reports/engineering_v14.json),
методика: [qa-v14.md](qa-v14.md).

Перевірено сім алгоритмів, сумісність SQLite/CAS і схем 2–6, JSON import/export,
ratings/watched/watchlist/exclusions/Undo, дві мови, disambiguation, namespace
IDs, offline кеш та відсутність credential/private-DB commits. Оригінальні
числові формули й production Adaptive default збережено; той самий benchmark
дає той самий SHA256 результатів. Усі початкові reports/configs з final v1.3
залишилися byte-for-byte незмінними. +17,8% залишається непідтвердженим;
cohort із 326 користувачів не запускали повторно.

## 5–7. Функціональність, PRs і UX

| PR | Вміст | База |
|---|---|---|
| [#20](https://github.com/Bandoof/CineMatch/pull/20) | Реальна добірка без ключа, українські labels, exact dedup, коректні помилки/empty states | main |
| [#21](https://github.com/Bandoof/CineMatch/pull/21) | Синтетичний профіль, окремий public pack, ізоляція сесій і reset | #20 branch |
| [#22](https://github.com/Bandoof/CineMatch/pull/22) | Реальний browser/axe QA, ресурси, Docker, доступність і явний вибір алгоритму | #21 branch |
| [#23](https://github.com/Bandoof/CineMatch/pull/23) | Двомовний README, кейс, схема, screenshots, scripts і hosting review | #22 branch |

Усі залишаються **OPEN, unmerged**. Default Adaptive не підмінено іншим режимом.
Collaborative можна вибрати явно для показу матричної факторизації. Відсутність
навченої Adaptive-політики або Semantic text artifact пояснено біля результатів.
Нові назви мають окремі жанрові/metadata heuristics, не вигадані ML-прогнози.

Поліпшено перший запуск, український пошук, порожні результати й бібліотеку,
видимі provider/cache errors, короткі source-описи, compact branded fallbacks,
підписану пагінацію, alt-текст і keyboard focus. Demo controls перенесено з
проблемної sidebar в основну сторінку. Виявлені ARIA-дефекти Streamlit 1.54
зумовили перевірене оновлення до 1.65. Приклади стану чітко відрізняються від
постійного приватного профілю. JSON import у публічному candidate entry відсутній.

## 8. Каталог і українське покриття

Фіксована відтворювана добірка: **30 реальних назв — 22 фільми й 8 серіалів**.
30/30 мають source-linked українську назву; 25/30 — короткий опис українською;
8 — TVmaze poster links та атрибутовані community ratings. 19 назв мають source
release year ≥2023; 5 мають точну дату в останніх 730 днях. Для 9 неоднозначних
або відсутніх точних дат збережено доступний рік, без удаваної календарної точності.

Initial capture: 14 live requests; уточнення labels: 4 live / 10 cache hits;
остаточна offline реконструкція: **0 live / 14 hits**. Fixtures, QIDs/TVmaze IDs,
retrieval dates і snapshot hash збережено в assets/demo. Це покриття маленької
добірки, не всього каталогу чи українського кінематографа. Фільмові ratings і
сучасну popularity не вигадано. TMDB credential у доступному середовищі не було:
live TMDB не перевірено, optional support/setup збережено. MovieLens залишається
історичною навчальною базою; TVmaze — джерелом серіалів.

Wikidata structured data/labels — CC0; TVmaze metadata adaptations — CC BY-SA
4.0 із джерелами/атрибуцією. Нові screenshots не містять сторонніх постерів.
Повну сторонню ліцензійну відповідність чи права на будь-яке artwork не сертифіковано.
[Джерела й обмеження](catalog-v14.md), [ліцензія](../assets/demo/LICENSE.md).

## 9–10. Ізоляція, браузер і доступність

Dedicated entry `app/portfolio_app.py` не створює SQLite/profile store/provider
client, не імпортує visitor files і не використовує provider credentials.
Mutable preferences, engine LRU та search index належать сесії. Seed/reset
відтворювані; refresh повертає початковий приклад. Public pack: 222 films,
30 000 вхідних development events / 29 974 canonical latest events, 248 combined
identities. Дані й model files залишаються поза Git.

AppTest із заборонними spies перевірив приватні storage/provider paths, дві
незалежні сесії, Undo/reset і точну формулу. Реальні browser contexts підтвердили,
що rating у A не з’являється у B. Налаштований SQLite sentinel не створюється;
глобальний profile LRU не зростав у тесті п’яти engines.

Playwright 1.63 / Chromium 153: **19 сценаріїв**, desktop 1440×1000, mobile
390×844, tablet 768×1024; **0 JavaScript errors / 0 failed requests** у passing
controlled run. Окремо перевірено видиме invalid-pack warning та metadata fallback,
без зміни файлів. Internet-offline тест вимикає posters, блокує зовнішній HTTPS
і залишає localhost websocket; це не offline PWA і не робота без Streamlit server.

Axe 4.14 на семи settled views: 0 violations; один ARIA finding — **incomplete**,
потребує ручної перевірки. Focus видимий, 3 px. Це не WCAG certification.
Потрібні NVDA/VoiceOver, opened controls, slider announcements, 200% zoom, touch
targets і реальні пристрої. Native accessibility strings частково англійські.
Ізоляцію перевірено локально/CI, не на ще неіснуючому публічному deployment.

## 11. Продуктивність

Та сама synthetic fixture, 1 BLAS thread, 1500 items / 100 users / 2400 events,
8 factors / 3 epochs / 20 repetitions:

| Метрика | Integrated v1.3 | v1.4 спостереження |
|---|---:|---:|
| Cold AppTest | 393,87 ms | 410,73 ms |
| Warm rerun | 14,99 ms | 20,47 ms |
| Recommendation output hash | `9efaf4a6…` | Той самий |

Є невелика **регресія**, а не заявлений приріст. Історичні 46,43→16,34 ms та
2625,68→265,43 ms збережено як історію; вони не є поточним guaranteed baseline.
10 000-title search зберіг 6/6 правильних top results. П’ять public-pack engines
дали peak близько 122 MiB; core score/search/facade timings записані у JSON.
Малий pack не порівнюється з історичним facade на 11 096 items.

Linux 6.18.44, Python 3.11.16, NumPy 1.26.4; managed quota 2 CPU equivalents / 8 GiB.
Browser/transport і Docker/CLI health latency виміряні окремо. Docker працює
як nonroot, без мережі й опублікованих портів у smoke test. Ці дані не доводять
production throughput, ML quality чи захист від необмежених visitor sessions.

## 12–13. Матеріали та хостинг

Створено двомовний [README](../README.md), [інженерний кейс](portfolio-case-study.md),
[Mermaid diagram](architecture-v14.md), [13 реальних screenshots](../assets/v14/README.md)
із hashes/provenance, [4-хвилинний storyboard і UA/EN narration](demo-video-v14.md),
два draft SRT та recording settings. Реальний silent QA MP4: 65,44 s, 1280×720,
H.264; representative frames переглянуто. Це **не готовий озвучений ролик**.
Сам відеофайл збережено локально поза Git та **не завантажено/не опубліковано**,
оскільки для відеопублікації немає дозволу; у PR збережено лише metadata/hash.

Рекомендація: Streamlit Community Cloud як початковий free metadata-only показ;
повний ML pack — локально/у майбутньому перевіреному immutable build.
Актуальні HF docs вимагають paid plan для створення Docker compute Spaces,
хоч CPU Basic має 0 hourly charge, 2 vCPU/16 GB. Render free має 15-minute idle
sleep, 750 hours/workspace/month та ephemeral disk. Числову Community Cloud/
Render memory guarantee тут не підтверджено. [Порівняння й owner checklist](hosting-v14.md).

## 14–16. Обмеження, дії власника й порядок злиття

Безпечний visitor entry реалізовано й перевірено, але hosting admission/DoS
ліміти та platform-specific isolation потребують перевірки точного deployment.
Ніякі private profiles/keys не слід переносити на хостинг. Artwork requests
розкривають TVmaze мережеві дані браузера; posters можна вимкнути.

Власнику потрібно: переглянути й зрозуміти AI-assisted зміни, виконати ручну
accessibility перевірку, записати та переглянути озвучений walkthrough,
вирішити public-pack/data/artwork terms і окремо дозволити публікацію відео,
deployment чи Release. Не приписуйте непереглянуті AI-generated зміни особистому
авторству. Дозвіл на ці зовнішні дії зараз не запитувався й не припускався.

Рекомендований порядок review/merge: **#20 → #21 → #22 → #23**. Кожен наступний
PR після owner-approved злиття попереднього потрібно retarget на main і
перевірити свіжий diff/head CI. Нові v1.4 PRs автоматично не зливаються.

## 17–18. Готовність і напрям v2.0

Кандидат готовий до технічного review та локального показу рекрутеру: основні
сценарії працюють, ML/heuristics розділені поясненнями, докази й recovery state
збережені в GitHub. Це не опублікований release чи сертифікований multiuser service.
Готовий озвучений відеоролик і public deployment — наступні owner-approved кроки.

Для v2.0 доречні: новий pre-registered evaluation на невикористаних даних,
легітимне ширше українське metadata coverage, калібровані пояснення та виміряні
hosting/session budgets. Зберігайте local-first/Streamlit і не перетворюйте цей
портфоліо-проєкт на комерційну платформу без окремого обґрунтування.
