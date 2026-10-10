# Search and discovery / Пошук і відкриття

The index searches original, Ukrainian, English and verified alternate titles.
It retains every canonical ID: title similarity is retrieval evidence, never an
identity join. Exact and prefix matches rank above substrings, mixed-title token
matches and bounded typo matches. Accent-insensitive Léon/Leon and literal 1+1
work; four-character or longer queries can use trigram candidates and SequenceMatcher
at a 0.72 threshold. Fuzzy comparisons are bounded to 200 candidates per query
representation. One/two-character queries use token prefixes rather than broad
fuzzy matching. Results have deterministic ID tie breaks.

Practical Ukrainian-to-Latin transliteration follows word-initial Є/Ї/Й/Ю/Я and
usual Ukrainian mappings. It is not translation and does not guarantee all informal
Romanization spellings. Exact UK and EN aliases remain searchable. Mixed queries
can match tokens across aliases. A trailing explicit year disambiguates remakes;
the title `1917` itself is not mistaken for its release year.

Filters cover media, genres, years and known community ratings; a positive rating
threshold excludes missing ratings. A 5-point MovieLens average converts to its
10-point equivalent for filtering only. That conversion does not calibrate sources
or predict enjoyment. Sorting supports relevance, newest, title, community average
and recorded vote count. Missing dates/ratings remain missing. All local search
works without providers, credentials or embeddings.

## Honest shelves

| Collection | Definition |
| --- | --- |
| Recently released | Provider release date in the past 730 days, newest first |
| Upcoming | Verified future provider date within 180 days, nearest first |
| Popular in the film catalog | Highest recorded MovieLens rating counts; historical reach |
| Hidden gems | MovieLens films: average >=4/5, >=5 ratings and count <= median among films with >=5 ratings |
| Because you liked | Positive genre cosine to an actually saved >=4-star title; highest rating then ID selects the seed |
| Movies for tonight | Released provider movies with an actual runtime <=130 minutes |

These are disclosed discovery heuristics, not new benchmark winners or live trends.
Rated/watched/dismissed/snoozed titles are excluded from recommendation shelves;
ordinary search still finds them for editing. A missing or empty feed has an honest
empty state. Upcoming films require valid cached metadata or the optional TMDB token.

Українською: пошук працює за оригінальною, українською, англійською та перевіреними
альтернативними назвами, підтримує помилки й практичну транслітерацію. Ремейки та
однойменні фільми/серіали залишаються окремими. Колекції мають явні визначення;
історичні оцінки MovieLens не називаються «трендами». Відсутні дані не вигадуються.
