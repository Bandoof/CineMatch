"""Presentation-only original illustrations; catalog metadata is never rewritten."""

from base64 import b64encode
from functools import lru_cache
from html import escape
from pathlib import Path

ARTWORK_DIR = Path(__file__).resolve().parents[1] / "assets" / "artwork"
# Explicit Wikidata identities, not fuzzy title matching or generated provider URLs.
ARTWORK = {
    108839994: "oppenheimer",
    109228991: "dune-part-two",
    112977213: "mickey-17",
    113380226: "the-substance",
    113877606: "inside-out-2",
    114246242: "f1",
    116025865: "past-lives",
    116361132: "nosferatu",
    116542843: "20-days-in-mariupol",
    117085614: "one-battle-after-another",
    123185887: "anora",
    124378349: "the-wild-robot",
    125473145: "sinners",
    125622088: "flow",
    13417189: "interstellar",
    172241: "the-shawshank-redemption",
    20382729: "arrival",
    28704028: "mavka",
    55436290: "barbie",
    60834962: "dune",
    83495: "the-matrix",
    83808444: "everything-everywhere-all-at-once",
}


@lru_cache(maxsize=len(ARTWORK))
def _encoded_artwork(slug):
    return b64encode((ARTWORK_DIR / f"{slug}.svg").read_bytes()).decode("ascii")


def original_artwork(title, display_title, notice):
    """Return local illustrated markup only for an approved film with no poster.

    Provider posters always win. Unknown films and series keep the neutral fallback.
    Callers retain the user's poster visibility preference.
    """
    if (
        title is None
        or title.poster_url
        or title.provider != "Wikidata"
        or title.media_type != "Movie"
        or title.provider_id not in ARTWORK
    ):
        return ""
    slug = ARTWORK[title.provider_id]
    try:
        encoded = _encoded_artwork(slug)
    except OSError:
        return ""  # A missing packaged illustration must not break discovery.
    return (
        '<div class="cinema-original-art">'
        f'<img src="data:image/svg+xml;base64,{encoded}" alt="" aria-hidden="true">'
        '<div class="cinema-art-caption">'
        f'<span class="cinema-art-title">{escape(display_title)}</span>'
        f'<span class="cinema-art-notice">{escape(notice)}</span>'
        "</div></div>"
    )
