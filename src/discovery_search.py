"""Indexed bilingual title retrieval. Matching never changes canonical identity."""

import bisect
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.search import normalize_text

TRANSLITERATION = dict(
    zip(
        "абвгґдеєжзиіїйклмнопрстуфхцчшщьюяыэъ",
        (
            "a",
            "b",
            "v",
            "h",
            "g",
            "d",
            "e",
            "ie",
            "zh",
            "z",
            "y",
            "i",
            "i",
            "i",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "r",
            "s",
            "t",
            "u",
            "f",
            "kh",
            "ts",
            "ch",
            "sh",
            "shch",
            "",
            "iu",
            "ia",
            "y",
            "e",
            "",
        ),
    )
)
INITIAL = {"є": "ye", "ї": "yi", "й": "y", "ю": "yu", "я": "ya"}


def transliterate(value):
    text, beginning = [], True
    for char in str(value).casefold():
        text.append(
            INITIAL.get(char, TRANSLITERATION.get(char, char))
            if beginning
            else TRANSLITERATION.get(char, char)
        )
        beginning = not char.isalpha()
    return "".join(text)


def names(value):
    body = re.sub(r"\s*\(\d{4}\)\s*$", "", value).strip()
    article = re.match(r"(.+), (The|A|An)$", body)
    variants = [value, body, f"{article[2]} {article[1]}" if article else body]
    return tuple(
        dict.fromkeys(
            normalize_text(v)
            for raw in variants
            for v in (raw, transliterate(raw))
            if normalize_text(v)
        )
    )


def grams(text):
    return {text[i : i + 3] for i in range(max(0, len(text) - 2))}


@dataclass(frozen=True)
class SearchRecord:
    item_id: int
    titles: tuple[str, ...]
    media_type: str
    year: int
    genres: tuple[str, ...]
    rating_10: float | None = None
    vote_count: int | None = None


@dataclass(frozen=True)
class SearchHit:
    item_id: int
    score: float
    match: str


def catalog_records(view):
    records = []
    for mid, row in view.rows.items():
        aliases = [str(row.title), view.display_title(mid, "en"), view.display_title(mid, "uk")]
        provider = view.titles.get(mid)
        rating, votes = None, None
        if provider:
            aliases += [
                provider.original_title,
                provider.title_en,
                provider.title_uk,
                *provider.alternate_titles,
            ]
            rating, votes = provider.community_rating, provider.vote_count
        elif view.base is not None:
            i = view.base.positions[mid]
            if row.media_type == "Series":
                raw = view.base.rows[mid].provider_rating
                rating = None if raw is None or raw != raw else float(raw)
            elif view.base.popularity.counts[i] > 0:
                rating = float(view.base.popularity.averages[i]) * 2
                votes = int(view.base.popularity.counts[i])
            item = view.base.metadata.items.get(mid, {})
            aliases += item.get("search_aliases", [])
            alternate = getattr(row, "alternate_title", "")
            if isinstance(alternate, str):
                aliases.append(alternate)
        records.append(
            SearchRecord(
                mid,
                tuple(dict.fromkeys(a for a in aliases if isinstance(a, str) and a)),
                row.media_type,
                int(row.year),
                tuple(row.genres),
                rating,
                votes,
            )
        )
    return records


class SearchIndex:
    def __init__(self, records):
        self.records = {r.item_id: r for r in records}
        self.names, self.tokens = {}, {}
        self.postings, self.ngrams = defaultdict(set), defaultdict(set)
        for mid, record in self.records.items():
            variants = tuple(dict.fromkeys(v for title in record.titles for v in names(title)))
            self.names[mid] = variants
            tokens = set(" ".join(variants).split())
            self.tokens[mid] = tokens
            for token in tokens:
                self.postings[token].add(mid)
            for gram in set().union(*(grams(v) for v in variants)):
                self.ngrams[gram].add(mid)
        self.words = sorted(self.postings)

    def _prefix(self, word):
        position = bisect.bisect_left(self.words, word)
        result = set()
        while position < len(self.words) and self.words[position].startswith(word):
            result.update(self.postings[self.words[position]])
            position += 1
        return result

    def search(
        self,
        query="",
        *,
        media_type="All",
        genres=(),
        year_range=None,
        min_rating=0,
        sort="relevance",
        limit=48,
    ):
        if media_type not in ("All", "Movie", "Series") or not 0 <= min_rating <= 10:
            raise ValueError("Invalid search filters.")
        if sort not in ("relevance", "newest", "title", "rating", "votes"):
            raise ValueError("Invalid search sort.")
        queries = tuple(
            dict.fromkeys((normalize_text(query), normalize_text(transliterate(query))))
        )
        queries = tuple(q for q in queries if q)
        selected_year = re.search(r"(?:\s|\()(\d{4})\)?$", query.strip())
        selected_year = int(selected_year[1]) if selected_year else None
        candidates, fuzzy = set(), set()
        if not queries:
            candidates = set(self.records)
        for needle in queries:
            tokens = needle.split()
            token_sets = [self._prefix(t) for t in tokens]
            if token_sets:
                candidates.update(set.intersection(*token_sets))
            query_grams = grams(needle)
            if query_grams:
                literal_sets = [self.ngrams.get(g, set()) for g in query_grams]
                candidates.update(set.intersection(*literal_sets))
            if len(needle) >= 4:
                counts = Counter(mid for g in query_grams for mid in self.ngrams.get(g, ()))
                fuzzy.update(
                    mid for mid, count in sorted(counts.items(), key=lambda r: (-r[1], r[0]))[:200]
                )
        hits = []
        for mid in candidates | fuzzy:
            record = self.records[mid]
            if (
                media_type != "All"
                and record.media_type != media_type
                or genres
                and not set(genres).intersection(record.genres)
                or year_range
                and not year_range[0] <= record.year <= year_range[1]
                or selected_year is not None
                and selected_year != record.year
                or min_rating > 0
                and (record.rating_10 is None or record.rating_10 < min_rating)
            ):
                continue
            score, match = (1.0, "browse") if not queries else (0.0, "")
            for needle in queries:
                for name in self.names[mid]:
                    if name == needle:
                        candidate_score, kind = 100, "exact"
                    elif name.startswith(needle):
                        candidate_score, kind = 90, "prefix"
                    elif len(needle) >= 3 and needle in name:
                        candidate_score, kind = 80, "partial"
                    elif all(
                        any(word.startswith(token) for word in self.tokens[mid])
                        for token in needle.split()
                    ):
                        candidate_score, kind = 70, "mixed_titles"
                    elif len(needle) >= 4 and mid in fuzzy:
                        similarity = SequenceMatcher(None, needle, name, autojunk=False).ratio()
                        candidate_score, kind = (
                            (similarity * 60, "typo") if similarity >= 0.72 else (0, "")
                        )
                    else:
                        candidate_score, kind = 0, ""
                    if candidate_score > score:
                        score, match = candidate_score, kind
            if score:
                hits.append(SearchHit(mid, score, match))

        def ordering(hit):
            r = self.records[hit.item_id]
            value = {
                "newest": -r.year,
                "title": normalize_text(r.titles[0]),
                "rating": -(r.rating_10 if r.rating_10 is not None else -1),
                "votes": -(r.vote_count if r.vote_count is not None else -1),
                "relevance": -hit.score,
            }[sort]
            return value, hit.item_id

        return (
            sorted(hits, key=ordering)[:limit] if limit is not None else sorted(hits, key=ordering)
        )
