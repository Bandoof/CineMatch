# Modern catalog providers / Сучасні джерела каталогу

MovieLens observations remain training/development data. Modern discovery is a
separate, bounded metadata snapshot; provider scores are attributed community
averages, never fabricated individual interactions or ALS predictions.

| Provider | Access | Useful metadata | Requirements |
| --- | --- | --- | --- |
| TVmaze | Public, no key | Series search, premiere dates, synopsis, genres, posters, runtime, cast/crew | CC BY-SA; source links and ShareAlike for redistributed adaptations |
| Wikidata | Public, no key | Film/series identities, IMDb links, Ukrainian/English labels, dates, genres | CC0 structured data |
| MovieLens | Existing explicit download | Historical film catalog and actual rating observations | Original GroupLens dataset terms; not a live-release catalog |
| ~~TMDB~~ | **Disabled** | — | See [Why TMDB is disabled](#why-tmdb-is-disabled--чому-tmdb-вимкнено) |

Official documentation: [TVmaze API](https://www.tvmaze.com/api) (inspected on
10 October 2026), [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing).
Recheck current terms before deployment or commercial use. Metadata/artwork and
provider trademarks are not relicensed under this repository's MIT code license.

## Why TMDB is disabled / Чому TMDB вимкнено

The [TMDB API Terms of Use](https://www.themoviedb.org/api-terms-of-use), read on
**14 November 2026**, list among the restrictions that the APIs or TMDB Content
must not be used in connection with, including for training, a machine learning
or artificial intelligence based application. The same terms limit caching to six
months and require purging cached TMDB Content when the license ends.
CineMatch is a recommender (an ML application), so TMDB is removed rather than
kept as an optional source. This is a summary, not legal advice; read the terms.

What changed in code: no TMDB requests, token, image host, parser, feeds or
attribution logo remain. Its former ID ranges (`-1_000_000_000_000 - id` and
`-2_000_000_000_000 - id`) stay reserved so they are never reused, and old local
records in those ranges are **skipped**, not shown or used:

- a local `catalog.json` that still contains TMDB records loads without them and
  shows a short count; the file itself is not rewritten when it is only loaded;
- an autosaved profile containing TMDB entries is loaded without them. Before
  autosave rewrites it, the original stored document is copied once to
  `<profile database>.pre-tmdb-removal.json` (default
  `data/profiles.sqlite3.pre-tmdb-removal.json`); an existing copy is never
  replaced. Imported or named profiles are read the same way, without changes to
  the stored source.

### Removing old TMDB data manually / Як видалити старі дані TMDB вручну

The application does not delete your files. If you ever used a TMDB token,
remove the cached TMDB content yourself (stop the app first):

1. **Response cache** `data/discovery/responses/` — file names are hashes, so
   TMDB responses cannot be told apart by name. Delete the whole directory; it is
   a cache, and TVmaze/Wikidata responses are fetched again on the next refresh.
   - bash: `rm -r data/discovery/responses`
   - PowerShell: `Remove-Item -Recurse data\discovery\responses`
2. **Saved catalog** `data/discovery/catalog.json` — run
   `python -m scripts.sync_catalog --offline` once. It loads the snapshot without
   TMDB records and saves it back, using only cached data (no network requests).
3. **Profile copy** `data/profiles.sqlite3.pre-tmdb-removal.json` (only if it was
   created) — it keeps your original profile, including TMDB entries. Delete it
   when you no longer need it.

If you used `--directory` or `CINEMATCH_DISCOVERY_DIR` / `CINEMATCH_PROFILE_DB`,
apply the same steps to those paths.

## Configuration

No key is needed for TVmaze, Wikidata, existing recommendations or offline operation.

```bash
python -m scripts.sync_catalog --pages 3
python -m scripts.sync_catalog --offline
python -m streamlit run app/catalog_explorer.py --server.address=127.0.0.1
```

`--directory` selects an independent metadata/cache directory. The application
uses `CINEMATCH_DISCOVERY_DIR` (default `data/discovery`). All downloads are
explicit; a search query is sent to providers only when requested. Profiles,
ratings and SQLite data are never sent. Provider search covers TVmaze series;
films come from the curated, dated snapshot. No fake release list replaces
missing provider data.

## Identity and scoring

Existing MovieLens positive IDs/aliases and TVmaze `-show_id` remain unchanged.
Wikidata movies use `-3_000_000_000_000 - id`; Wikidata series use
`-4_000_000_000_000 - id`. IDs are integers within SQLite/int64 range. Provider
IDs are limited to 1–999,999,999 to keep namespaces disjoint. The external key
also explicitly includes provider and media type.

A unique IMDb ID **plus matching media type and release year** can join verified
metadata to an existing item; an existing TVmaze ID is authoritative for TVmaze.
Mapping provenance is recorded in the catalog facade. Title-only/fuzzy matches
never merge items. Ambiguous IDs, remakes and movie/series namesakes stay separate.
The original training engine is reused without refitting its weights or changing
its numerical outputs. Modern-only suggestions use a disclosed signed genre
affinity/provider-quality heuristic in a separate collection. They have no
collaborative evidence, and are not an experimentally validated new policy.

## Caches, offline use and validation

HTTPS uses system CA trust and the configured proxy. Only fixed provider hosts
and supported endpoint patterns are requested. Redirects are refused. Each request
has an 8-second timeout, 4 MB response cap and JSON validation. Requests are
serialized at least 0.6 seconds apart, below TVmaze's published minimum of 20
requests per 10 seconds. HTTP 429 uses bounded Retry-After cooldown instead of
blocking UI retries. Failures return neutral status codes; exception bodies/URLs
are not displayed.

The response cache is bounded to 100 files / 100 MB, with a six-hour fresh TTL and
14-day maximum stale fallback. Corrupt, oversized, future-dated or expired entries
are ignored. Cache filenames hash provider/endpoint/parameters and contain no
raw search query. Read-only storage does not prevent a live response.
The explicitly saved catalog is a bounded offline snapshot (5,000 identities /
30 MB read cap), not a guarantee of current releases; original fetch dates are
retained and shown. Refresh replaces metadata atomically; it never edits training
datasets, model weights, benchmark reports or personal databases.

Only allowlisted HTTPS artwork hosts are accepted (TVmaze and Wikimedia). TVmaze
permits image hotlinking. The client stores URLs, not bulk artwork.
Missing images/text/ratings remain missing. Synopsis HTML is converted to text;
provider HTML/JavaScript is never injected. Exact UK metadata falls back to EN,
then available original metadata. No translation or rating is generated.

## Attribution

Each title links to its provider. TVmaze metadata is credited **TVmaze · CC BY-SA**;
Wikidata structured data is CC0 and linked to its item.

Українською: сучасний каталог відокремлено від навчальних оцінок MovieLens.
TVmaze і Wikidata працюють без ключів. **TMDB вимкнено**: його умови API (прочитано
14.11.2026) забороняють використання у зв'язку з ML/AI-застосунками, зокрема для
навчання, а CineMatch — рекомендаційна система. Старі локальні записи TMDB
приховуються й не використовуються; оригінал автозбереженого профілю один раз
копіюється перед перезаписом. Кеш і файли застосунок не видаляє — інструкцію
див. вище. Оновлення й зовнішній пошук виконуються явно. Особисті оцінки/профілі
залишаються локально. Без мережі використовується датований збережений каталог;
відсутні постери, переклади та рейтинги не вигадуються. Дані TVmaze — CC BY-SA.
