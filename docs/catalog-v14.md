# Credential-free discovery / Відкритий демонстраційний каталог

The shipped **real** dated sample contains 22 movies / 8 series, 30 source-provided
Ukrainian titles, 25 Ukrainian short descriptions, eight poster links and eight
attributed TVmaze community ratings. Wikidata films deliberately have no invented
ratings/posters/synopses. See [measured coverage](../assets/demo/coverage.json),
[identities](../assets/demo/sources.json), [snapshot](../assets/demo/catalog.json)
and [separate data license](../assets/demo/LICENSE.md).

IMDb claims resolved through the official Wikidata SPARQL endpoint identify the
curated QIDs. Bounded official `wbgetentities` batches obtain UK/EN labels and
structured statements. Genres/directors are prioritized before a capped set of
cast labels. The client permits only read actions, 20 IDs/request, fixed HTTPS
hosts, existing response/cache caps, timeout/429 cooldown and at least one second
between Wikidata requests. No HTML scraping, API token, artwork download or
generated translation is involved. A live search investigation received 429;
it was stopped. Snapshot rebuilding uses explicit identities, not mass search.

Wikidata film IDs: `-3_000_000_000_000-QID`; series: `-4_000_000_000_000-QID`.
Existing MovieLens/TVmaze/TMDB identities stay supported. Unique IMDb + media type
+ year can join distinct providers; same-provider duplicates, missing evidence,
type conflicts and remakes stay separate. Provider aliases normalize profiles;
primary references remain exportable schema 6. Original training scores do not
change. Wikidata localizations carry their own source links.

Rebuild to an independent directory, preserving the committed snapshot:

```bash
python -m scripts.build_portfolio_catalog --online --output data/portfolio-metadata/catalog.json --cache data/portfolio-metadata/responses
# Repeat without network; cached original retrieval dates remain unchanged:
python -m scripts.build_portfolio_catalog --output data/portfolio-metadata/catalog.json --cache data/portfolio-metadata/responses
```

A partial/failed refresh refuses to replace the previous output. The sample
fallback is used only when no historical data and no local snapshot exist; it
never overwrites a saved catalog/profile. External search failures now appear
on the page with useful status text; a failed cache save is explicitly session-only.

Українською: це невелика реальна датована добірка з українськими назвами Wikidata,
а не вигаданий повний каталог. Збережений файл працює офлайн; опис Wikidata —
короткий фактографічний опис, не згенерований сюжет. Постери потребують мережі.
Облікові дані TMDB відсутні в доступному середовищі, live TMDB не перевірено;
налаштування й контрактні тести збережено. Для актуального широкого каталогу
власник може явно оновити TVmaze або налаштувати необов’язковий TMDB.
