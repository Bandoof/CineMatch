# Modern catalog providers / Сучасні джерела каталогу

MovieLens observations remain training/development data. Modern discovery is a
separate, bounded metadata snapshot; provider scores are attributed community
averages, never fabricated individual interactions or ALS predictions.

| Provider | Access | Useful metadata | Requirements |
| --- | --- | --- | --- |
| TVmaze | Public, no key | Series search, premiere dates, synopsis, genres, posters, runtime, cast/crew | CC BY-SA; source links and ShareAlike for redistributed adaptations |
| TMDB | Optional free developer read token | Recent/upcoming movies, movie/TV search, UK/EN titles and synopsis, artwork, credits, official trailers | Noncommercial developer use with attribution/logo; separate commercial license |
| MovieLens | Existing explicit download | Historical film catalog and actual rating observations | Original GroupLens dataset terms; not a live-release catalog |

Official documentation inspected on 10 October 2026:
[TVmaze API](https://www.tvmaze.com/api),
[TMDB FAQ and terms summary](https://developer.themoviedb.org/docs/faq),
[rate limiting](https://developer.themoviedb.org/docs/rate-limiting),
[images](https://developer.themoviedb.org/docs/image-basics),
[now playing](https://developer.themoviedb.org/reference/movie-now-playing-list),
[upcoming](https://developer.themoviedb.org/reference/movie-upcoming-list).
Recheck current terms before deployment or commercial use. Metadata/artwork and
provider trademarks are not relicensed under this repository's MIT code license.

## Configuration

No key is needed for TVmaze, existing recommendations or offline operation.
Optionally set **TMDB_READ_ACCESS_TOKEN** to your developer API Read Access Token
in the process environment. Obtain it through your own TMDB account; never put
the value in code, Git, a URL, screenshots or a shared profile. Restart after
changing credentials. No paid API or account is provisioned automatically.

```bash
python -m scripts.sync_catalog --pages 3
python -m scripts.sync_catalog --offline
python -m streamlit run app/catalog_explorer.py --server.address=127.0.0.1
```

`--directory` selects an independent metadata/cache directory. The application
uses `CINEMATCH_DISCOVERY_DIR` (default `data/discovery`). All downloads are
explicit; a search query is sent to providers only when requested. Profiles,
ratings and SQLite data are never sent. Credentials stay in request headers.
With no TMDB token, current movie feeds are unavailable and clearly identified;
cached movies and the historical film catalog remain useful. No fake release
list replaces missing provider data.

## Identity and scoring

Existing MovieLens positive IDs/aliases and TVmaze `-show_id` remain unchanged.
TMDB movies use `-1_000_000_000_000 - id`; TMDB TV uses
`-2_000_000_000_000 - id`. IDs are integers within SQLite/int64 range. Provider
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
and supported endpoint patterns are requested. Redirects are refused, including
redirects that might forward authorization. Each request has an 8-second timeout,
4 MB response cap and JSON validation. Requests are serialized at least 0.6 seconds
apart, below TVmaze's published minimum of 20 requests per 10 seconds. HTTP 429
uses bounded Retry-After cooldown instead of blocking UI retries. Failures return
neutral status codes; exception bodies/URLs/tokens are not displayed.

The response cache is bounded to 100 files / 100 MB, with a six-hour fresh TTL and
14-day maximum stale fallback. Corrupt, oversized, future-dated or expired entries
are ignored. Cache filenames hash provider/endpoint/parameters and contain no
credential or raw search query. Read-only storage does not prevent a live response.
The explicitly saved catalog is a bounded offline snapshot (5,000 identities /
30 MB read cap), not a guarantee of current releases; original fetch dates are
retained and shown. Refresh replaces metadata atomically; it never edits training
datasets, model weights, benchmark reports or personal databases.

Only allowlisted HTTPS artwork hosts are accepted. TVmaze permits image hotlinking;
TMDB images use its documented CDN. The client stores URLs, not bulk artwork.
Missing images/text/ratings remain missing. Synopsis HTML is converted to text;
provider HTML/JavaScript is never injected. Trailer links require an official
YouTube Trailer record and a valid video ID. Exact UK metadata falls back to EN,
then available original metadata. No translation or rating is generated.

## Attribution

Each title links to its provider. TVmaze metadata is credited **TVmaze · CC BY-SA**.
When TMDB data is used, display the unchanged approved logo from
[official logos](https://www.themoviedb.org/about/logos-attribution) and the notice:
**This product uses the TMDB API but is not endorsed or certified by TMDB.**
`assets/tmdb-approved.svg` is an unchanged official approved short logo; its
trademark use follows TMDB's rules and is separate from the code license.

Українською: сучасний каталог відокремлено від навчальних оцінок MovieLens.
TVmaze працює без ключа; сучасні фільми TMDB потребують необов'язкового власного
read token. Оновлення й зовнішній пошук виконуються явно. Особисті оцінки/профілі
залишаються локально. Без мережі використовується датований збережений каталог;
відсутні постери, переклади та рейтинги не вигадуються. Дані TVmaze — CC BY-SA,
TMDB потребує логотипа/notice, а комерційне використання — окремої ліцензії.
