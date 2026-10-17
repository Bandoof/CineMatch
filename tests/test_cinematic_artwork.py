"""Original artwork must stay local, labeled and outside catalog/profile data."""

from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree

from streamlit.testing.v1 import AppTest

from app.cinematic_artwork import ARTWORK, ARTWORK_DIR, original_artwork
from src.portfolio import sample_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_all_22_missing_film_posters_have_distinct_self_contained_artwork():
    catalog = sample_catalog(ROOT)
    films = [t for t in catalog.titles.values() if t.media_type == "Movie"]
    assert len(films) == len(ARTWORK) == 22
    assert {t.provider_id for t in films} == set(ARTWORK)
    drawings = set()
    for title in films:
        assert not title.poster_url
        raw = (ARTWORK_DIR / f"{ARTWORK[title.provider_id]}.svg").read_text(encoding="utf-8")
        root = ElementTree.fromstring(raw)
        assert root.attrib["viewBox"] == "0 0 400 600"
        assert "Not an official movie poster" in raw
        assert all(
            el.tag.split("}")[-1] not in {"image", "script", "foreignObject"} for el in root.iter()
        )
        assert not any("href" in attr for el in root.iter() for attr in el.attrib)
        drawings.add(raw)
        rendered = original_artwork(title, title.title("uk"), "Оригінальна ілюстрація")
        assert "data:image/svg+xml;base64," in rendered
        assert "Оригінальна ілюстрація" in rendered
    assert len(drawings) == 22


def test_provider_posters_series_and_unknown_titles_are_never_replaced():
    catalog = sample_catalog(ROOT)
    series = [t for t in catalog.titles.values() if t.media_type == "Series"]
    assert len(series) == 8
    for title in series:
        assert title.poster_url.startswith("https://static.tvmaze.com/")
        assert original_artwork(title, title.original_title, "Original artwork") == ""
    film = next(t for t in catalog.titles.values() if t.media_type == "Movie")
    assert not original_artwork(replace(film, poster_url=series[0].poster_url), "x", "x")
    assert not original_artwork(replace(film, provider_id=1), "x", "x")
    assert not original_artwork(None, "x", "x")


def test_artwork_escapes_text_and_preserves_metadata():
    film = next(t for t in sample_catalog(ROOT).titles.values() if t.media_type == "Movie")
    before = repr(film)
    markup = original_artwork(film, '<script>alert("x")</script>', "<img src=x>")
    assert "<script>" not in markup and "&lt;script&gt;" in markup
    assert "&lt;img src=x&gt;" in markup
    assert repr(film) == before and not film.poster_url


def test_cards_details_languages_and_poster_toggle(monkeypatch):
    monkeypatch.setenv("CINEMATCH_MODE", "portfolio")
    monkeypatch.setenv("CINEMATCH_DEFAULT_LANGUAGE", "en")
    app = AppTest.from_file(str(ROOT / "app/portfolio_app.py"), default_timeout=30).run()
    assert not app.exception
    app.button_group(key="navigation_en").set_value("search").run()
    app.text_input(key="query_search").set_value("Oppenheimer").run()
    assert any("Original artwork" in m.value for m in app.markdown)
    view = app.session_state["_portfolio_view"]
    mid = next(mid for mid, t in view.titles.items() if t.original_title == "Oppenheimer")
    app.button(key=f"details_search_{mid}").click().run()
    assert any("Original artwork" in m.value for m in app.markdown)
    app.selectbox(key="ui_language").set_value("uk").run()
    assert any("Оригінальна ілюстрація" in m.value for m in app.markdown)
    app.checkbox(key="posters").uncheck().run()
    assert not any("cinema-original-art" in m.value for m in app.markdown)
    assert any("Постери вимкнено" in m.value for m in app.markdown)
    app.checkbox(key="posters").check().run()
    assert any("Оригінальна ілюстрація" in m.value for m in app.markdown)
    assert not app.exception


def test_missing_local_artwork_renders_neutral_fallback(monkeypatch, tmp_path):
    """A missing asset with posters enabled must fall back without altering metadata."""
    import app.cinematic_artwork as artwork

    monkeypatch.setattr(artwork, "ARTWORK_DIR", tmp_path)
    artwork._encoded_artwork.cache_clear()

    def render(root):
        import streamlit as st

        from app.product_ui import artwork
        from src.catalog_view import CatalogView
        from src.portfolio import sample_catalog

        st.session_state.update(ui_language="uk", posters=True)
        view = CatalogView(None, sample_catalog(root))
        mid = next(mid for mid, t in view.titles.items() if t.original_title == "Oppenheimer")
        artwork(view, mid)

    try:
        app = AppTest.from_function(render, args=(str(ROOT),), default_timeout=30).run()
        assert not app.exception
        markup = next(m.value for m in app.markdown if "cinema-poster-fallback" in m.value)
        assert "Постер недоступний" in markup and "Оппенгеймер" in markup
        assert not any("cinema-original-art" in m.value for m in app.markdown)
    finally:
        artwork._encoded_artwork.cache_clear()
