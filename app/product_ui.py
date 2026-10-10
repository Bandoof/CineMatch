"""CineMatch consumer surface. Native controls, bounded lists, optional metadata."""

import os
import sqlite3
from pathlib import Path

import numpy as np
import streamlit as st

from app import memory as local_memory
from app.catalog_explorer import provider_client, provider_credits, save_catalog
from app.recommender import ALGORITHMS
from app.runtime import artifact_signature, load_runtime
from src.catalog_view import CatalogView
from src.discovery import discovery_queue
from src.discovery_collections import collections
from src.discovery_search import SearchIndex, catalog_records
from src.i18n import genre_name, model_name, tr
from src.library_actions import change, undo
from src.metadata import trusted_url
from src.modern_catalog import IMAGE_HOSTS, ModernCatalog
from src.profile_actions import replace_profile
from src.profiles import ProfileStore, export_profile, import_library_profile, import_topics
from src.providers import provider_search, refresh_catalog, title_details

ROOT = Path(__file__).resolve().parents[1]
PAGES = ("discover", "for_you", "movies", "series", "search", "library", "research")
PAGE_LABELS = {
    "discover": ("Відкривайте", "Discover"),
    "for_you": ("Для вас", "For You"),
    "movies": ("Фільми", "Movies"),
    "series": ("Серіали", "TV Series"),
    "search": ("Пошук", "Search"),
    "library": ("Моя бібліотека", "My Library"),
    "research": ("Дослідження", "Research"),
}


def s(uk, en):
    return uk if st.session_state.get("ui_language", "uk") == "uk" else en


def language():
    return st.session_state.ui_language


def choice(label, options, key, labels, container=st, radio=False, **kwargs):
    """Keep canonical values while remounting translated native widget labels."""
    options = list(options)
    value = st.session_state.get(key, options[0])
    selected = options.index(value) if value in options else 0
    render = container.radio if radio else container.selectbox
    result = render(
        label, options, index=selected, key=f"{key}_{language()}", format_func=labels.get, **kwargs
    )
    st.session_state[key] = result
    return result


def index(view):
    key = (id(view), view.revision)
    if st.session_state.get("_search_revision") != key:
        st.session_state._search_index = SearchIndex(catalog_records(view))
        st.session_state._search_revision = key
    return st.session_state._search_index


def load_view():
    directory = Path(os.environ.get("CINEMATCH_DATA_DIR", ROOT / "data" / "ml-100k"))
    discovery_dir = Path(os.environ.get("CINEMATCH_DISCOVERY_DIR", ROOT / "data" / "discovery"))
    series = Path(os.environ.get("CINEMATCH_SERIES_FILE", ROOT / "data" / "tvmaze" / "series.json"))
    metadata = Path(
        os.environ.get("CINEMATCH_METADATA_FILE", ROOT / "data" / "metadata" / "catalog.json")
    )
    content = Path(os.environ.get("CINEMATCH_CONTENT_FILE", metadata.parent / "content.json"))
    artifacts = Path(os.environ.get("CINEMATCH_ARTIFACT_ROOT", ROOT))
    modern = directory.parent / "ml-latest-small"
    files = [
        directory / "u.data",
        directory / "u.item",
        series,
        metadata,
        content,
        modern / "movies.csv",
        modern / "ratings.csv",
        modern / "links.csv",
        *[
            artifacts / part
            for part in (
                "models/full.npz",
                "models/expanded.npz",
                "reports/metrics.json",
                "reports/expanded_metrics.json",
                "reports/ml_v3.json",
            )
        ],
    ]
    signature = artifact_signature(files)
    base = None
    if all((directory / name).is_file() for name in ("u.data", "u.item")):
        with st.spinner(s("Готуємо ваш кінопростір…", "Preparing your cinema…")):
            base, _, _, _ = load_runtime(
                str(directory), str(series), str(artifacts), signature, str(metadata), str(content)
            )
    catalog_path = discovery_dir / "catalog.json"
    view_key = (id(base), artifact_signature([catalog_path]))
    if st.session_state.get("_view_key") != view_key:
        bundled_sample = base is None and not catalog_path.exists()
        try:
            catalog = ModernCatalog.load(
                ROOT / "assets/demo/catalog.json" if bundled_sample else catalog_path
            )
        except (OSError, ValueError):
            catalog = ModernCatalog()
            st.warning(
                s(
                    "Не вдалося прочитати кеш каталогу. Збережений файл не змінено.",
                    "The catalog cache could not be read. The saved file was preserved.",
                )
            )
        old = st.session_state.get("_catalog_view")
        view = CatalogView(base, catalog)
        view.bundled_sample = bundled_sample
        if old is not None:
            ids = set(st.session_state.get("ratings", {}))
            for key in ("blocked", "watched", "watchlist", "not_seen", "snoozed"):
                ids.update(st.session_state.get(key, ()))
            view.adopt_references(view.with_references(old.export_references(ids)))
        st.session_state._catalog_view = view
        st.session_state._view_key = view_key
    return st.session_state._catalog_view, discovery_dir


def perform(mid, action, rating=None):
    change(st.session_state, mid, action, rating)
    st.session_state._feedback = s("Збережено у вашій бібліотеці", "Saved to your library")
    st.rerun()


def open_details(mid):
    st.session_state.selected_title = mid
    st.query_params["title"] = str(mid)
    st.rerun()


def navigate():
    st.session_state.pop("selected_title", None)
    st.query_params.pop("title", None)


def search_page():
    st.session_state.navigation = "search"
    st.session_state[f"navigation_{language()}"] = "search"
    navigate()


def poster(view, mid):
    title = view.titles.get(mid)
    if title:
        return title.poster_url
    if view.base is not None and mid in view.base.positions:
        return trusted_url(view.base.metadata.poster(view.base.rows[mid]), IMAGE_HOSTS)
    return ""


def artwork(view, mid, width=None):
    url = poster(view, mid) if st.session_state.get("posters", True) else ""
    if url:
        st.image(url, width=width or "stretch")
    else:
        with st.container(key="poster_missing" if width else f"missing_{mid}"):
            st.caption("◉  CineMatch")
            st.caption(s("Постер недоступний", "Poster unavailable"))


def source_rating(view, mid):
    title = view.titles.get(mid)
    if title and title.community_rating is not None:
        return f"{title.provider} · {title.community_rating:g}/10"
    if view.base is not None and mid in view.base.positions:
        i = view.base.positions[mid]
        if view.base.popularity.counts[i]:
            return (
                f"MovieLens · {view.base.popularity.averages[i]:.1f}/5 · {int(view.base.popularity.counts[i])} "
                + s("оцінок", "ratings")
            )
        value = view.base.rows[mid].provider_rating
        if np.isfinite(value):
            return f"TVmaze · {value:g}/10"
    return ""


def cards(view, identities, prefix, reasons=None, empty_text=None):
    ids = list(dict.fromkeys(int(mid) for mid in identities if mid in view.rows))[:12]
    if not ids:
        st.info(
            empty_text
            or s(
                "Тут поки немає назв. Спробуйте інший жанр, пошук або додайте кілька оцінок.",
                "No titles here yet. Try another genre, a search, or a few ratings.",
            )
        )
        return
    for start in range(0, len(ids), 3):
        for col, mid in zip(st.columns(3, gap="large"), ids[start : start + 3]):
            with col, st.container(border=True, key=f"card_{prefix}_{mid}"):
                # Every item occupies one bounded native column; mobile stacks natively.
                if poster(view, mid) and st.session_state.get("posters", True):
                    st.image(poster(view, mid), width="stretch")
                else:
                    with st.container(height=240, border=False):
                        st.write("◉")
                        st.caption(s("Постер недоступний", "Poster unavailable"))
                row = view.rows[mid]
                st.subheader(view.display_title(mid, language()))
                st.caption(
                    s("Серіал", "Series") if row.media_type == "Series" else s("Фільм", "Movie")
                )
                st.caption(" · ".join(genre_name(g, language()) for g in row.genres[:3]))
                if source_rating(view, mid):
                    st.caption(source_rating(view, mid))
                if mid in st.session_state.ratings:
                    st.caption(
                        s("Ваша оцінка", "Your rating")
                        + f" · ★ {st.session_state.ratings[mid]:g}/5"
                    )
                elif mid in st.session_state.watched:
                    st.caption(s("✓ Переглянуто", "✓ Watched"))
                elif mid in st.session_state.watchlist:
                    st.caption(s("✓ У списку", "✓ Watchlisted"))
                if reasons and mid in reasons:
                    st.caption(reasons[mid])
                if st.button(
                    s("Детальніше", "Details"),
                    key=f"details_{prefix}_{mid}",
                    width="stretch",
                ):
                    open_details(mid)
                if st.button(
                    s("Прибрати зі списку", "Remove from watchlist")
                    if mid in st.session_state.watchlist
                    else s("Дивитися пізніше", "Watchlist"),
                    key=f"watch_{prefix}_{mid}",
                    width="stretch",
                    disabled=mid in st.session_state.watched,
                ):
                    perform(mid, "watchlist")


def exclusions():
    return st.session_state.blocked | st.session_state.snoozed | st.session_state.watched


def provider_controls(view, directory):
    with st.sidebar.expander(s("Каталог і джерела", "Catalog & sources")):
        st.caption(
            s(
                "Збережені назви працюють без інтернету. Оновлення надсилає лише запит каталогу.",
                "Saved titles work offline. Refresh sends only a catalog request.",
            )
        )
        st.caption(f"{len(view.movies)} " + s("назв", "titles"))
        if getattr(view, "bundled_sample", False):
            st.caption(
                s(
                    "Невелика датована демонстраційна добірка. Це не повний сучасний каталог.",
                    "Small dated demonstration selection. This is not a complete contemporary catalog.",
                )
            )
        st.caption(
            s(
                "Нові фільми: необов’язковий TMDB. Серіали: TVmaze без ключа.",
                "New movies: optional TMDB. Series: TVmaze, no key required.",
            )
        )
        if st.button(s("Оновити каталог", "Refresh catalog"), key="refresh_catalog"):
            client = provider_client(str(directory), os.environ.get("TMDB_READ_ACCESS_TOKEN", ""))
            titles, statuses = refresh_catalog(client, online=True)
            if titles:
                view.add_titles(titles)
                st.session_state._metadata_save_failed = not save_catalog(view.catalog, directory)
            st.session_state.provider_status = statuses
            st.rerun()
        if st.session_state.get("provider_status"):
            statuses = st.session_state.provider_status.values()
            if any(value not in ("fetched", "cache") for value in statuses):
                st.caption(
                    s(
                        "Частина джерел недоступна; використовуємо збережені дані.",
                        "Some sources are unavailable; saved data remains available.",
                    )
                )
        stamps = [t.fetched_utc[:10] for t in view.titles.values() if t.fetched_utc]
        if stamps:
            st.caption(
                s("Останнє отримання метаданих: ", "Latest metadata retrieval: ") + max(stamps)
            )
        provider_credits(view.catalog)


def provider_feedback():
    statuses = st.session_state.get("provider_status", {})
    messages = {
        "missing_credentials": s(
            "не налаштовано необов’язковий токен", "optional token is not configured"
        ),
        "offline": s("офлайн; збережені назви доступні", "offline; saved titles remain available"),
        "stale": s("використано давніший кеш", "older cached metadata was used"),
        "rate_limited": s("ліміт запитів; повторіть пізніше", "rate limited; try later"),
        "unavailable": s(
            "джерело недоступне; дані збережено", "source unavailable; existing data preserved"
        ),
    }
    failures = [
        f"{source}: {messages[value]}"
        for source, value in statuses.items()
        if value in messages
        and source
        in {"TVmaze", "TVmaze schedule", "TMDB", "TMDB now_playing", "TMDB upcoming", "Wikidata"}
    ]
    if failures:
        st.warning(" · ".join(failures))
    if st.session_state.get("_metadata_save_failed"):
        st.warning(
            s(
                "Метадані доступні лише в цій сесії: запис кешу не вдався.",
                "Metadata is available in this session only: the cache could not be saved.",
            )
        )


def discover(view):
    shelves = collections(view, st.session_state.ratings, exclusions(), limit=6)
    sample = getattr(view, "bundled_sample", False)
    if sample:
        eligible = [
            mid
            for mid in view.rows
            if mid not in exclusions() and mid not in st.session_state.ratings
        ]
        shelves["sample"] = [mid for mid in eligible if view.rows[mid].media_type == "Series"][
            :3
        ] + [mid for mid in shelves["recent"] if view.rows[mid].media_type == "Movie"][:3]
    st.session_state.setdefault(
        "discovery_shelf", "sample" if sample else "recent" if shelves["recent"] else "popular"
    )
    with st.container(key="cinema_hero"):
        st.caption(s("ВАШ НАСТУПНИЙ КІНОВЕЧІР", "YOUR NEXT MOVIE NIGHT"))
        st.title(s("Історії, що залишаються з вами.", "Stories that stay with you."))
        st.write(
            s(
                "Знаходьте фільми й серіали за настроєм. Зберігайте цікаве. Дайте своєму смаку голос.",
                "Find films and series for your mood. Save a possibility. Give your taste a voice.",
            )
        )
        st.button(
            s("Знайти свою історію", "Find your story"),
            key="hero_search",
            type="primary",
            on_click=search_page,
        )
    shelf = choice(
        s("Що відкриємо сьогодні?", "What shall we discover?"),
        (["sample"] if sample else [])
        + ["recent", "popular", "hidden_gems", "upcoming", "tonight", "because_liked"],
        labels={
            "sample": s("Добірка для знайомства", "Portfolio selection"),
            "recent": s("Нещодавно вийшли", "Recently released"),
            "popular": s("Популярні в MovieLens", "Popular in MovieLens"),
            "hidden_gems": s("Приховані перлини", "Hidden gems"),
            "upcoming": s("Незабаром", "Upcoming"),
            "tonight": s("Фільми на вечір", "Movies for tonight"),
            "because_liked": s("Тому що вам сподобалося", "Because you liked"),
        },
        key="discovery_shelf",
    )
    definitions = {
        "sample": s(
            "Невелика датована добірка реальних серіалів і фільмів. Це не рейтинг популярності.",
            "Small dated selection of real series and films. This is not a popularity ranking.",
        ),
        "recent": s(
            "Перша дата виходу за останні 730 днів; тільки підтверджені дати провайдерів.",
            "First release within 730 days; verified provider dates only.",
        ),
        "upcoming": s(
            "Підтверджена майбутня дата в межах 180 днів; дати можуть змінюватися.",
            "Verified future date within 180 days; dates may change.",
        ),
        "popular": s(
            "За кількістю історичних оцінок MovieLens. Це не поточні тренди.",
            "By historical MovieLens rating count. This is not a current trend.",
        ),
        "hidden_gems": s(
            "MovieLens: середня ≥4/5, щонайменше 5 оцінок і кількість не вище медіани.",
            "MovieLens: mean ≥4/5, at least 5 ratings, count at or below the median.",
        ),
        "tonight": s(
            "Фільми з підтвердженою тривалістю ≤130 хвилин, які вже вийшли.",
            "Released movies with verified runtime ≤130 minutes.",
        ),
        "because_liked": s(
            "Схожість реальних жанрів із вашою оцінкою ≥4/5.",
            "Actual genre similarity to a title you rated ≥4/5.",
        ),
    }
    st.caption(definitions[shelf])
    if shelf == "because_liked" and shelves["seed"] is not None:
        st.write(view.display_title(shelves["seed"], language()))
    cards(view, shelves[shelf], "discover")
    if not len(view.movies):
        st.info(
            s(
                "Почніть із оновлення каталогу в меню «Каталог і джерела» або пошуку серіалу.",
                "Start with Refresh catalog in Catalog & sources, or search for a series.",
            )
        )


def browse(view, directory, page):
    st.title(PAGE_LABELS[page][0 if language() == "uk" else 1])
    query = st.text_input(
        s("Назва, рік або частина назви", "Title, year or part of a title"),
        key=f"query_{page}",
        max_chars=160,
    )
    media = "Movie" if page == "movies" else "Series" if page == "series" else "All"
    with st.expander(s("Фільтри та порядок", "Filters & sorting")):
        if page == "search":
            media = choice(
                s("Тип", "Media"),
                ["All", "Movie", "Series"],
                key="search_media",
                labels={
                    "All": s("Усе", "All"),
                    "Movie": s("Фільми", "Movies"),
                    "Series": s("Серіали", "Series"),
                },
            )
        genres = st.multiselect(
            s("Жанри", "Genres"),
            view.content.genre_names if view.content else [],
            key=f"genres_{page}_{language()}",
            default=[
                g
                for g in st.session_state.get(f"genres_{page}", [])
                if view.content and g in view.content.genre_names
            ],
            format_func=lambda g, lang=language(): genre_name(g, lang),
        )
        st.session_state[f"genres_{page}"] = genres
        known_years = [int(r.year) for r in view.rows.values() if r.year]
        years = None
        if known_years and min(known_years) < max(known_years):
            years = st.slider(
                s("Роки виходу", "Release years"),
                min(known_years),
                max(known_years),
                (min(known_years), max(known_years)),
                key=f"years_{page}",
            )
        rating = st.slider(
            s("Мінімальна оцінка джерела /10", "Minimum source rating /10"),
            0.0,
            10.0,
            0.0,
            0.5,
            key=f"rating_{page}",
        )
        st.caption(
            s(
                "MovieLens /5 перераховано в /10 лише для фільтра; відсутні оцінки не вигадуємо.",
                "MovieLens /5 is scaled to /10 for this filter only; missing ratings remain missing.",
            )
        )
        sort = choice(
            s("Порядок", "Sort"),
            ["relevance", "newest", "title", "rating", "votes"],
            key=f"sort_{page}",
            labels={
                "relevance": s("За відповідністю", "Relevance"),
                "newest": s("Новіші спочатку", "Newest"),
                "title": s("За назвою", "Title"),
                "rating": s("За оцінкою джерела", "Source rating"),
                "votes": s("За кількістю оцінок", "Rating count"),
            },
        )
    hits = index(view).search(
        query,
        media_type=media,
        genres=genres,
        year_range=years,
        min_rating=rating,
        sort=sort,
        limit=None,
    )
    signature = (query, media, tuple(genres), years, rating, sort, view.revision)
    if st.session_state.get(f"browse_signature_{page}") != signature:
        st.session_state[f"page_{page}"] = 1
        st.session_state[f"browse_signature_{page}"] = signature
    pages = max(1, (len(hits) + 11) // 12)
    number = int(
        st.number_input(
            s("Сторінка", "Page"), min_value=1, max_value=pages, step=1, key=f"page_{page}"
        )
    )
    st.caption(f"{len(hits)} " + s("результатів", "results"))
    cards(
        view,
        [hit.item_id for hit in hits[(number - 1) * 12 : number * 12]],
        page,
        empty_text=s(
            "Збігів немає. Спробуйте іншу назву, приберіть рік або послабте фільтри. Збережений каталог може бути неповним.",
            "No matches. Try another title, remove the year or relax filters. The saved catalog may be incomplete.",
        ),
    )
    if query.strip():
        with st.expander(s("Шукати поза збереженим каталогом", "Search beyond the saved catalog")):
            st.caption(
                s(
                    "Надсилається лише текст цього пошуку. Оцінки та бібліотека залишаються локально.",
                    "Only this search text is sent. Your ratings and library stay local.",
                )
            )
            if st.button(s("Пошук у джерелах", "Search providers"), key=f"remote_{page}"):
                client = provider_client(
                    str(directory), os.environ.get("TMDB_READ_ACCESS_TOKEN", "")
                )
                titles, statuses = provider_search(client, query, media_type=media, online=True)
                if titles:
                    view.add_titles(titles)
                    st.session_state._metadata_save_failed = not save_catalog(
                        view.catalog, directory
                    )
                st.session_state.provider_status = statuses
                if titles:
                    st.session_state._feedback = s(
                        "Знайдені метадані додано до каталогу",
                        "Matching metadata added to the catalog",
                    )
                st.rerun()


def details(view, directory, mid):
    if st.button(s("← Повернутися", "← Back"), key="detail_back"):
        st.session_state.pop("selected_title", None)
        st.query_params.pop("title", None)
        st.rerun()
    row, title = view.rows[mid], view.titles.get(mid)
    if title and title.backdrop_url and st.session_state.get("posters", True):
        st.image(title.backdrop_url, width="stretch")
    image, content = st.columns([1, 2], gap="large")
    with image:
        artwork(view, mid, width=320)
    with content:
        st.title(view.display_title(mid, language()))
        if title and title.original_title != title.title(language()):
            st.caption(title.original_title)
        st.write(" · ".join(genre_name(g, language()) for g in row.genres))
        if source_rating(view, mid):
            st.write(source_rating(view, mid))
        if title:
            short = (
                title.short_description_uk if language() == "uk" else ""
            ) or title.short_description_en
            if short:
                st.caption(s("Короткий опис Wikidata: ", "Wikidata short description: ") + short)
            if title.localization_source:
                st.link_button(
                    s("Джерело української назви ↗", "Ukrainian title source ↗"),
                    title.localization_source,
                )
            if title.release_date:
                st.caption(s("Перша дата виходу: ", "First release: ") + title.release_date)
            if title.runtime:
                st.caption(s("Тривалість: ", "Runtime: ") + f"{title.runtime} " + s("хв", "min"))
            if title.status:
                st.caption(title.status)
            if title.summary(language()):
                st.write(title.summary(language()))
                if language() == "uk" and not title.summary_uk:
                    st.caption(
                        s(
                            "Український опис поки недоступний; показано опис джерела.",
                            "Ukrainian synopsis unavailable; showing the source synopsis.",
                        )
                    )
            if title.cast:
                st.write(s("У ролях: ", "Cast: ") + ", ".join(title.cast))
            if title.creators:
                st.write(s("Автори та команда: ", "Creators & crew: ") + ", ".join(title.creators))
            if title.trailer_url:
                st.link_button(s("Офіційний трейлер ↗", "Official trailer ↗"), title.trailer_url)
            st.link_button(title.provider + s(" · джерело ↗", " · source ↗"), title.source_url)
            if title.fetched_utc:
                st.caption(
                    s("Метадані отримано: ", "Metadata retrieved: ") + title.fetched_utc[:10]
                )
            if mid in view.reference_only:
                st.info(
                    s(
                        "Збережену назву відновлено з профілю. Повні метадані можна оновити.",
                        "Saved identity restored from your profile. Full metadata can be refreshed.",
                    )
                )
            if st.button(s("Оновити деталі", "Refresh details"), key="refresh_details"):
                client = provider_client(
                    str(directory), os.environ.get("TMDB_READ_ACCESS_TOKEN", "")
                )
                refreshed, status = title_details(client, title, online=True)
                if refreshed.fetched_utc:
                    view.add_titles([refreshed])
                    st.session_state._metadata_save_failed = not save_catalog(
                        view.catalog, directory
                    )
                st.session_state.provider_status = {title.provider: status}
                st.rerun()
        else:
            st.caption(
                s(
                    "Додаткові метадані цієї назви поки недоступні.",
                    "Additional metadata for this title is unavailable.",
                )
            )
            if view.base and view.base.semantic:
                item = (
                    view.base.semantic.items.get(mid, {})
                    if hasattr(view.base.semantic, "items")
                    else {}
                )
                summary = (item.get("summary_uk") if language() == "uk" else "") or item.get(
                    "summary_en"
                )
                if summary:
                    st.write(summary)
            if view.base:
                source = view.base.metadata.image_source(view.base.rows[mid])
                if source:
                    st.link_button(s("Джерело зображення ↗", "Artwork source ↗"), source)
        st.divider()
        if mid in st.session_state.ratings:
            st.caption(
                s("Ваша оцінка", "Your rating") + f" · ★ {st.session_state.ratings[mid]:g}/5"
            )
        with st.form(f"rating_form_{mid}"):
            rating = st.select_slider(
                s("Ваша оцінка /5", "Your rating /5"),
                options=[i / 2 for i in range(1, 11)],
                value=st.session_state.ratings.get(mid, 4.0),
                key=f"stars_{mid}",
            )
            if st.form_submit_button(s("Зберегти оцінку", "Save rating"), type="primary"):
                perform(mid, "rate", rating)
        a, b = st.columns(2)
        if a.button(
            s("Прибрати зі списку", "Remove from watchlist")
            if mid in st.session_state.watchlist
            else s("Дивитися пізніше", "Watchlist"),
            key="detail_watchlist",
            disabled=mid in st.session_state.watched,
            width="stretch",
        ):
            perform(mid, "watchlist")
        if b.button(
            s("✓ Переглянуто", "✓ Watched"),
            key="detail_watched",
            disabled=mid in st.session_state.watched,
            width="stretch",
        ):
            perform(mid, "watched")
        with st.expander(s("Інші дії", "More actions")):
            if mid in st.session_state.watched:
                st.caption(
                    s(
                        "Щоб повернути оцінену назву до непереглянутих, спершу приберіть свою оцінку.",
                        "To mark a rated title unwatched, first remove your rating.",
                    )
                )
                if st.button(
                    s("Позначити непереглянутим", "Mark unwatched"),
                    key="detail_unwatch",
                    disabled=mid in st.session_state.ratings,
                ):
                    perform(mid, "unwatch")
            if st.button(
                s("Повернути до рекомендацій", "Show in recommendations again")
                if mid in st.session_state.blocked
                else s("Не цікавить", "Not interested"),
                key="detail_hide",
            ):
                perform(mid, "hide")
            if st.button(
                s("Повернути зараз", "Bring back now")
                if mid in st.session_state.snoozed
                else s("Відкласти на цю сесію", "Snooze for this session"),
                key="detail_snooze",
            ):
                perform(mid, "snooze")
            if mid in st.session_state.ratings and st.button(
                s("Прибрати мою оцінку", "Remove my rating"), key="detail_unrate"
            ):
                perform(mid, "remove_rating")
    st.subheader(s("Схожі за жанрами", "Similar genres"))
    similarities = view.content.features @ view.content.features[view.positions[mid]]
    similar = [
        other
        for other in sorted(view.rows, key=lambda i: (-similarities[view.positions[i]], i))
        if other != mid and other not in exclusions() and similarities[view.positions[other]] > 0
    ][:3]
    cards(view, similar, "similar")


def for_you(view):
    st.title(s("Кіно у вашому смаку", "Cinema for your taste"))
    if not st.session_state.ratings:
        st.info(
            s(
                "Оцініть кілька знайомих історій — і підбір стане особистішим. Почати можна без оцінок.",
                "Rate a few familiar stories to make discovery more personal. You can explore without ratings.",
            )
        )
    with st.expander(
        s("Кілька знайомих історій", "A few familiar stories"),
        expanded=not bool(st.session_state.ratings),
    ):
        ids = []
        if view.base is not None:
            known = set(view.base.positions)
            ids = discovery_queue(
                view.base,
                view.known_profile(st.session_state.ratings),
                st.session_state.not_seen & known,
                st.session_state.blocked & known,
                watched=st.session_state.watched & known,
            )[:3]
        if not ids:
            ids = [
                mid
                for mid, _ in view.modern_recommend(
                    st.session_state.ratings, exclusions() | st.session_state.not_seen, limit=3
                )
            ]
        if ids:
            mid = ids[0]
            st.subheader(view.display_title(mid, language()))
            with st.form(f"guide_{mid}"):
                rating = st.select_slider(
                    s("Як вам ця історія? /5", "How did you like it? /5"),
                    [i / 2 for i in range(1, 11)],
                    value=4.0,
                )
                if st.form_submit_button(s("Оцінити", "Rate")):
                    perform(mid, "rate", rating)
            if st.button(s("Не дивився / не дивилася", "Haven’t seen it"), key="guide_not_seen"):
                perform(mid, "not_seen")
            st.caption(
                s("Ця відповідь не є негативною оцінкою.", "This answer is not a negative rating.")
            )
    if view.base is not None:
        results = view.recommend_known(
            st.session_state.ratings,
            "Adaptive",
            k=6,
            blocked=st.session_state.blocked,
            watched=st.session_state.watched,
            snoozed=st.session_state.snoozed,
            topic_blocked=st.session_state.topic_blocked,
            language=language(),
            min_ratings=0,
        )
        st.subheader(s("Знайомий каталог · Adaptive", "Known catalog · Adaptive"))
        st.caption(
            s(
                "Наявна модель працює з оцінками відомих їй назв. Нові назви не додають вигаданих взаємодій.",
                "The existing model uses ratings of known titles. New titles never create fabricated interactions.",
            )
        )
        cards(
            view, [r.movie_id for r in results], "personal", {r.movie_id: r.reason for r in results}
        )
    modern = view.modern_recommend(st.session_state.ratings, exclusions(), limit=6)
    if modern:
        st.subheader(s("Нові можливості", "New possibilities"))
        st.caption(
            s(
                "Схожість жанрів із вашими оцінками та доступна оцінка джерела. Це не collaborative prediction.",
                "Genre affinity from your ratings and available source quality. This is not a collaborative prediction.",
            )
        )
        cards(view, [mid for mid, _ in modern], "modern")


def profile_controls(view):
    payload = export_profile(
        view,
        st.session_state.ratings,
        st.session_state.blocked,
        st.session_state.not_seen,
        st.session_state.watched,
        st.session_state.watchlist,
        st.session_state.topic_blocked,
    )
    with st.expander(s("Профілі та резервна копія", "Profiles & backup")):
        st.download_button(
            s("Експортувати JSON", "Export JSON"),
            payload,
            "cinematch-profile.json",
            "application/json",
            key="profile_export",
        )
        uploaded = st.file_uploader(
            s("Імпортувати профіль JSON", "Import profile JSON"), type="json", key="profile_upload"
        )

        def load(payload):
            try:
                values = import_library_profile(view, payload)
                topics = import_topics(view, payload)
            except (ValueError, TypeError, UnicodeError):
                st.error(
                    s(
                        "Профіль не прийнято. Поточні дані збережено.",
                        "Profile rejected. Your current data was preserved.",
                    )
                )
                return
            replace_profile(
                st.session_state,
                *values[:2],
                not_seen=values[2],
                watched=values[3],
                watchlist=values[4],
                topic_blocked=topics,
            )
            st.session_state.pop("library_undo", None)
            st.session_state.session_activity = {}
            st.rerun()

        if uploaded is not None and st.button(
            s("Завантажити JSON", "Load JSON"), key="profile_import"
        ):
            load(uploaded.getvalue())
        if os.environ.get("CINEMATCH_LOCAL_PROFILES", "1") == "1":
            store = ProfileStore(
                os.environ.get("CINEMATCH_PROFILE_DB", ROOT / "data" / "profiles.sqlite3")
            )
            try:
                names = store.names()
                name = st.text_input(
                    s("Назва профілю", "Profile name"), max_chars=80, key="profile_name"
                )
                if st.button(
                    s("Зберегти профіль", "Save profile"),
                    key="profile_save",
                    disabled=not name.strip(),
                ):
                    store.save(name, payload)
                    st.success(s("Профіль збережено", "Profile saved"))
                if names:
                    selected = st.selectbox(
                        s("Збережені профілі", "Saved profiles"), names, key="profile_selected"
                    )
                    if st.button(s("Завантажити профіль", "Load profile"), key="profile_load"):
                        load(store.load(selected))
            except (OSError, sqlite3.Error, ValueError):
                st.warning(
                    s(
                        "Локальне сховище недоступне; JSON і дані сесії залишаються доступними.",
                        "Local storage is unavailable; JSON and session data remain available.",
                    )
                )


def library(view):
    st.title(s("Ваша кінополиця", "Your cinema shelf"))
    a, b, c = st.columns(3)
    a.metric(s("Дивитися пізніше", "Watchlist"), len(st.session_state.watchlist))
    b.metric(s("Переглянуто", "Watched"), len(st.session_state.watched))
    c.metric(s("Оцінок", "Ratings"), len(st.session_state.ratings))
    groups = {
        "watchlist": s("Дивитися пізніше", "Watchlist"),
        "watched": s("Переглянуто", "Watched"),
        "ratings": s("Мої оцінки", "My ratings"),
        "blocked": s("Не цікавить", "Not interested"),
        "snoozed": s("Відкладено на сесію", "Snoozed this session"),
        "session_activity": s("Оновлено в цій сесії", "Updated this session"),
    }
    group = choice(
        s("Колекція", "Collection"),
        list(groups),
        labels=groups,
        radio=True,
        horizontal=True,
        key="library_group",
    )
    query_col, media_col, sort_col = st.columns([2, 1, 1])
    query = query_col.text_input(
        s("Пошук у бібліотеці", "Search your library"), max_chars=160, key="library_query"
    )
    media = choice(
        s("Тип у бібліотеці", "Library media"),
        ["All", "Movie", "Series"],
        key="library_media",
        container=media_col,
        labels={
            "All": s("Усе", "All"),
            "Movie": s("Фільми", "Movies"),
            "Series": s("Серіали", "Series"),
        },
    )
    sort = choice(
        s("Порядок бібліотеки", "Library sort"),
        ["title", "newest", "rating"],
        key="library_sort",
        container=sort_col,
        labels={
            "title": s("За назвою", "Title"),
            "newest": s("За роком виходу", "Release year"),
            "rating": s("За моєю оцінкою", "My rating"),
        },
    )
    selected = set(st.session_state[group])
    hits = [
        hit
        for hit in index(view).search(
            query, media_type=media, sort="newest" if sort == "newest" else "title", limit=None
        )
        if hit.item_id in selected
    ]
    if sort == "rating":
        hits.sort(key=lambda h: (-st.session_state.ratings.get(h.item_id, 0), h.item_id))
    if group == "session_activity":
        hits.sort(key=lambda h: st.session_state.session_activity[h.item_id], reverse=True)
        st.caption(
            s(
                "Лише реальні дії поточної сесії; історичних дат не додаємо.",
                "Actual changes in this session only; no historical dates are inferred.",
            )
        )
    signature = (group, query, media, sort, tuple(hit.item_id for hit in hits))
    if st.session_state.get("library_signature") != signature:
        st.session_state.library_page = 1
        st.session_state.library_signature = signature
    page = int(
        st.number_input(
            s("Сторінка бібліотеки", "Library page"),
            min_value=1,
            max_value=max(1, (len(hits) + 11) // 12),
            step=1,
            key="library_page",
        )
    )
    cards(
        view,
        [h.item_id for h in hits[(page - 1) * 12 : page * 12]],
        "library",
        empty_text=s(
            "У цій колекції немає збігів. Додайте назву з деталей або змініть фільтри бібліотеки.",
            "No matching titles in this collection. Add one from Details or change library filters.",
        ),
    )
    with st.expander(s("Ваш смак у цифрах", "Your taste in numbers")):
        counts = {}
        for mid in st.session_state.ratings:
            for genre in view.rows[mid].genres:
                counts[genre_name(genre, language())] = (
                    counts.get(genre_name(genre, language()), 0) + 1
                )
        if counts:
            st.bar_chart(counts, color="#e6b35a")
            st.caption(
                s(
                    "Кількість оцінених вами назв у кожному жанрі; багатожанрові назви враховано кілька разів.",
                    "Number of your rated titles per genre; multi-genre titles count in several genres.",
                )
            )
            values = list(st.session_state.ratings.values())
            st.caption(
                s("Середня ваша оцінка: ", "Your mean rating: ")
                + f"{sum(values) / len(values):.2f}/5"
            )
        else:
            st.info(s("Ваші оцінки з’являться тут.", "Your ratings will appear here."))
    profile_controls(view)


def research(view):
    st.title(s("Лабораторія рекомендацій", "Recommendation lab"))
    st.info(
        s(
            "Історичні +17,8% не підтверджено. Cohort v1.2 із 326 користувачів уже використано; це не новий holdout.",
            "Historical +17.8% is unverified. The 326-user v1.2 cohort is already consumed; it is not a new holdout.",
        )
    )
    if view.base is None:
        st.caption(
            s(
                "Дослідження доступні з локальним MovieLens-каталогом.",
                "Research is available with the local MovieLens catalog.",
            )
        )
        return
    from app.ml_lab import render

    algorithm = choice(
        s("Алгоритм", "Algorithm"),
        ALGORITHMS,
        key="algorithm",
        labels={v: model_name(v, language()) for v in ALGORITHMS},
    )
    minimum = st.select_slider(
        s("Мінімум оцінок MovieLens", "Minimum MovieLens ratings"),
        [0, 1, 5, 10, 20, 50],
        key="minimum",
    )
    diversity = st.slider(s("Різноманітність", "Diversity"), 0.0, 1.0, 0.0, 0.05, key="diversity")
    known = set(view.base.positions)
    filters = {
        key: st.session_state[key] & known
        for key in ("blocked", "topic_blocked", "snoozed", "watched")
    }
    filters.update(min_ratings=minimum, diversity=diversity, language=language())
    previous = st.session_state.get("recommendation_change")
    if previous:
        st.session_state.recommendation_change = {
            "profile": view.known_profile(previous["profile"]),
            **{
                key: previous[key] & known
                for key in ("blocked", "topic_blocked", "snoozed", "watched")
            },
        }
    try:
        render(
            view.base,
            view.known_profile(st.session_state.ratings),
            algorithm,
            filters,
            lambda key, **args: tr(key, language(), **args),
            language(),
        )
    finally:
        if previous is not None:
            st.session_state.recommendation_change = previous


def main():
    memory = local_memory.initialize(ROOT)
    try:
        _main(memory)
    finally:
        local_memory.save(memory)


def _main(memory):
    state = st.session_state
    state.setdefault("ui_language", os.environ.get("CINEMATCH_DEFAULT_LANGUAGE", "uk"))
    st.markdown(
        "<style>" + (ROOT / "app" / "product.css").read_text(encoding="utf-8") + "</style>",
        unsafe_allow_html=True,
    )
    with st.container(key="brand"):
        brand, control = st.columns([3, 1])
        brand.subheader("◉ CineMatch")
        control.selectbox(
            "Мова / Language",
            ["uk", "en"],
            key="ui_language",
            format_func=lambda v: "Українська" if v == "uk" else "English",
        )
    view, directory = load_view()
    local_memory.restore(memory, view)
    for key, default in (
        ("ratings", {}),
        ("blocked", set()),
        ("topic_blocked", set()),
        ("watched", set()),
        ("watchlist", set()),
        ("not_seen", set()),
        ("snoozed", set()),
        ("demo", False),
        ("guide_history", []),
        ("session_activity", {}),
    ):
        state.setdefault(key, default)
    try:
        state.ratings = view.validate_profile(state.ratings)
        for key in ("blocked", "topic_blocked", "watched", "watchlist", "not_seen", "snoozed"):
            state[key] = {view.normalize_id(mid) for mid in state[key]}
        state.topic_blocked &= state.blocked
        state.watched |= set(state.ratings)
        state.watchlist -= state.watched
        state.not_seen -= state.watched
    except (ValueError, TypeError):
        st.error(
            s(
                "Профіль не відповідає доступному каталогу. Дані збережено; відновіть потрібний каталог.",
                "The profile does not match this catalog. Data was preserved; restore the required catalog.",
            )
        )
        if memory:
            memory["ready"] = False
        return
    with st.sidebar:
        st.subheader(s("Ваш кінопростір", "Your cinema"))
        st.caption(s("Особисто. Локально. У вашому смаку.", "Personal. Local. Your taste."))
        st.caption(
            f"{len(state.watchlist)} "
            + s("у списку", "watchlisted")
            + f" · {len(state.ratings)} "
            + s("оцінок", "ratings")
        )
        local_memory.controls(memory, lambda key: tr(key, language()))
        st.checkbox(
            s("Показувати постери", "Show posters"), value=state.get("posters", True), key="posters"
        )
        if st.button(
            s("Скасувати останню дію", "Undo last action"),
            key="library_undo_button",
            disabled="library_undo" not in state,
        ):
            undo(state)
            state._feedback = s("Дію скасовано", "Action undone")
            st.rerun()
        provider_controls(view, directory)
    feedback = state.pop("_feedback", None)
    if feedback:
        st.toast(feedback)
    provider_feedback()
    page = choice(
        s("Навігація", "Navigation"),
        PAGES,
        key="navigation",
        horizontal=True,
        radio=True,
        labels={k: labels[0 if language() == "uk" else 1] for k, labels in PAGE_LABELS.items()},
        on_change=navigate,
    )
    if state.get("selected_title") is None and "title" in st.query_params:
        try:
            state.selected_title = view.normalize_id(st.query_params["title"])
        except (ValueError, TypeError):
            st.query_params.pop("title", None)
    mid = state.get("selected_title")
    if mid is not None and mid in view.rows:
        details(view, directory, mid)
    elif page == "discover":
        discover(view)
    elif page in ("movies", "series", "search"):
        browse(view, directory, page)
    elif page == "for_you":
        for_you(view)
    elif page == "library":
        library(view)
    else:
        research(view)
