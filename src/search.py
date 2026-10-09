"""Accent-insensitive bilingual title and alias search, with literal punctuation."""

import re
import unicodedata


def normalize_text(value):
    value = unicodedata.normalize("NFKD", str(value)).casefold()
    value = "".join(character for character in value if not unicodedata.combining(character))
    # Numeric '+' is part of a title, not a separator or regular expression.
    value = re.sub(r"(?<=\d)\s*\+\s*(?=\d)", "+", value)
    return re.sub(r"[^\w+]+", " ", value).strip()


def identity_keys(title):
    """Titles plus alternate names, always including their release year."""
    year_match = re.search(r"\((\d{4})\)\s*$", title)
    if not year_match:
        return set()
    year = year_match[1]
    body = title[:year_match.start()].strip()
    names = [re.sub(r"\([^)]*\)", "", body), *re.findall(r"\(([^)]*)\)", body)]
    keys = set()
    for name in names:
        name = re.sub(r"^a\.k\.a\.\s*", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r", (The|A|An)$", "", name, flags=re.IGNORECASE)
        name = re.sub(r"^(The|A|An) ", "", name, flags=re.IGNORECASE)
        if name:
            keys.add(normalize_text(name) + " " + year)
    return keys


def title_matches(query, *titles):
    needle = normalize_text(query)
    return bool(needle) and any(needle in normalize_text(title) for title in titles if isinstance(title, str))
