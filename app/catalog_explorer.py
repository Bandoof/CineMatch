"""Runnable catalog vertical slice; no training or private profile access required."""

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.catalog_view import CatalogView  # noqa: E402
from src.discovery_collections import collections  # noqa: E402
from src.discovery_search import SearchIndex, catalog_records  # noqa: E402
from src.modern_catalog import ModernCatalog  # noqa: E402
from src.providers import JsonCache, ProviderClient, provider_search, refresh_catalog  # noqa: E402


@st.cache_resource(show_spinner=False, max_entries=3)
def provider_client(directory, token):
    return ProviderClient(JsonCache(Path(directory) / "responses"), token=token)


def save_catalog(catalog, directory):
    try:
        catalog.save(Path(directory) / "catalog.json")
        return True
    except (OSError, ValueError):
        st.warning("Metadata could not be saved. Current results remain available.")
        return False


def provider_credits(catalog):
    st.caption("TVmaze metadata · CC BY-SA · Source links on every title")
    st.link_button("TVmaze · licensing", "https://www.tvmaze.com/api#licensing")
    if any(
        title.provider == "Wikidata" or title.localization_source
        for title in catalog.titles.values()
    ):
        st.caption(
            "Wikidata structured metadata / UK labels · CC0 · Dated sample, not a live release feed"
        )
        st.link_button("Wikidata · CC0", "https://www.wikidata.org/wiki/Wikidata:Licensing")
    if any(title.provider == "TMDB" for title in catalog.titles.values()):
        st.image(str(ROOT / "assets" / "tmdb-approved.svg"), width=90)
        st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")
        st.link_button("TMDB · attribution", "https://www.themoviedb.org/about/logos-attribution")


def main():
    st.title("CineMatch · Catalog explorer")
    st.caption("Optional provider metadata · no model training or personal profiles")
    directory = Path(os.environ.get("CINEMATCH_DISCOVERY_DIR", ROOT / "data" / "discovery"))
    try:
        catalog = ModernCatalog.load(directory / "catalog.json")
    except (ValueError, OSError):
        catalog = ModernCatalog()
        st.warning("The saved catalog could not be read. Existing data was preserved.")
    client = provider_client(str(directory), os.environ.get("TMDB_READ_ACCESS_TOKEN", ""))
    st.info(
        "TVmaze requires no key. TMDB movies require optional TMDB_READ_ACCESS_TOKEN. Cached titles work offline."
    )
    with st.form("catalog_query"):
        query = st.text_input("Title / Назва", max_chars=160)
        submitted = st.form_submit_button("Search providers / Пошук у джерелах")
    if submitted and query.strip():
        titles, statuses = provider_search(client, query, online=True)
        catalog.update(titles)
        st.caption(" · ".join(f"{k}: {v}" for k, v in statuses.items()))
        if titles:
            save_catalog(catalog, directory)
    if st.button("Refresh recent catalog / Оновити каталог"):
        titles, statuses = refresh_catalog(client, online=True)
        catalog.update(titles)
        if titles:
            save_catalog(catalog, directory)
        st.caption(" · ".join(f"{k}: {v}" for k, v in statuses.items()))
    st.caption(
        f"{len(catalog.titles)} saved titles · Provider dates are metadata, not viewing histories."
    )
    if not catalog.titles:
        st.info("Refresh or search to save a provider snapshot. No titles are invented.")
    view = CatalogView(None, catalog)
    local_query = st.text_input(
        "Search saved titles / Пошук у збереженому каталозі", key="local_query", max_chars=160
    )
    media = st.selectbox("Media / Тип", ["All", "Movie", "Series"], key="catalog_media")
    genres = st.multiselect(
        "Genres / Жанри", sorted({g for title in catalog.titles.values() for g in title.genres})
    )
    sort = st.selectbox(
        "Sort / Порядок", ["relevance", "newest", "title", "rating"], key="catalog_sort"
    )
    shelf = st.radio("Collection / Колекція", ["Browse", "Recent", "Upcoming"], horizontal=True)
    matches = SearchIndex(catalog_records(view)).search(
        local_query, media_type=media, genres=genres, sort=sort, limit=None
    )
    if shelf != "Browse":
        allowed = set(collections(view, limit=5000)["recent" if shelf == "Recent" else "upcoming"])
        matches = [hit for hit in matches if hit.item_id in allowed]
        st.caption(
            "Recent: released in the past 730 days. Upcoming: verified future dates within 180 days."
        )
    st.caption(f"{len(matches)} matching titles · showing at most 12")
    for hit in matches[:12]:
        title = view.titles[hit.item_id]
        with st.container(border=True):
            st.subheader(title.title("uk"))
            st.caption(f"{title.year or '—'} · {title.media_type} · {title.provider}")
            if title.summary("uk"):
                st.text(title.summary("uk")[:400])
            if title.community_rating is not None:
                st.caption(f"{title.provider}: {title.community_rating:g}/10")
            st.link_button(title.provider + " · source", title.source_url)
    provider_credits(catalog)


if __name__ == "__main__":
    main()
