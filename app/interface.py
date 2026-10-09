"""Bilingual CineMatch: films, real series and portable user profiles."""

import html
import os
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.recommender import ALGORITHMS  # noqa: E402
from app.runtime import artifact_signature, load_runtime  # noqa: E402
from src.i18n import genre_name, model_name, tr  # noqa: E402
from src.profiles import ProfileStore, export_profile, import_library_profile, import_topics  # noqa: E402
from src.discovery import discovery_queue  # noqa: E402
from src.search import title_matches  # noqa: E402
from app import memory as local_memory  # noqa: E402
from src import profile_actions  # noqa: E402


def replace_profile(ratings, blocked, demo=False, not_seen=None, watched=None, watchlist=None, topic_blocked=None):
    profile_actions.replace_profile(st.session_state, ratings, blocked, demo, not_seen,
                                    watched, watchlist, topic_blocked)
    st.rerun()


def main():
    memory = local_memory.initialize(ROOT)
    try:
        _main(memory)
    finally:
        # Button handlers call st.rerun immediately; save their changes before it unwinds.
        local_memory.save(memory)


def _main(memory):
    default_language = os.environ.get("CINEMATCH_DEFAULT_LANGUAGE", "uk")
    st.session_state.setdefault("ui_language", default_language)
    brand, language_control = st.columns([3, 1])
    brand.markdown('<div class="brand">🎬 CineMatch</div>', unsafe_allow_html=True)
    with language_control:
        language = st.selectbox("Мова / Language", ["uk", "en"], key="ui_language",
                                format_func=lambda value: "Українська" if value == "uk" else "English")
    t = lambda key, **values: tr(key, language, **values)  # noqa: E731
    st.markdown("""<style>
    .block-container{max-width:1230px;padding-top:1.3rem;padding-bottom:3rem}
    .brand{padding-left:40px;padding-top:.2rem;font-weight:750;font-size:1.05rem}
    h1,h2,h3{letter-spacing:-.035em;color:#17253a}
    header[data-testid="stHeader"]{background:transparent}
    .hero{padding:.7rem 1.5rem;border-radius:18px;background:#17253a;
    margin-bottom:1rem;position:relative;overflow:hidden}
    .hero:after{content:'◉';position:absolute;right:24px;top:-60px;font-size:220px;color:#e84f3e;opacity:.15}
    .eyebrow{color:#f9b5aa;letter-spacing:.17em;font-size:.7rem;font-weight:800}
    .hero h1{font-size:clamp(1.65rem,2.6vw,2.2rem);color:#fff;margin:.4rem 0;line-height:1.15}
    .hero p{color:#cbd2de;font-size:.95rem;margin:.7rem 0 0;max-width:620px;position:relative;z-index:1}
    .poster{width:100%;aspect-ratio:2/3;object-fit:cover;border-radius:12px;background:#eeece4;display:block}
    .guide-poster{height:320px;aspect-ratio:auto;object-fit:contain;background:#17253a}
    .poster-missing{height:300px;border-radius:12px;background:#eeece4;display:flex;
    flex-direction:column;align-items:center;justify-content:center;color:#6c7380}
    .poster-missing span{font-size:3rem}.poster-missing p{font-size:.8rem}
    .kind{font-size:.72rem;font-weight:800;color:#e84f3e;text-transform:uppercase;letter-spacing:.13em}
    div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px;border-color:#e0e0d8}
    div[data-testid="stTabs"] button{font-weight:650}
    section[data-testid="stSidebar"]{border-right:1px solid #deded6}
    section[data-testid="stSidebar"] h1{font-size:1.6rem}
    button[kind="primary"]{border-radius:12px}
    div[data-testid="stProgress"]{margin-bottom:.7rem}
    .st-key-guided_card div[data-testid="stVerticalBlock"]{gap:.6rem}
    .st-key-guided_card h3{font-size:1.45rem}
    .st-key-recommendation_grid h3{font-size:1.1rem;line-height:1.35;min-height:3rem}
    @media(max-width:800px){.st-key-recommendation_grid div[data-testid="stHorizontalBlock"]{flex-wrap:wrap}
    .st-key-recommendation_grid div[data-testid="stColumn"]{min-width:0;flex:0 0 calc(50% - .5rem);max-width:calc(50% - .5rem)}}
    @media(max-width:640px){.hero{padding:1.1rem}.guide-poster{height:310px}
    .st-key-recommendation_grid .poster{max-height:380px;object-fit:contain;background:#17253a}}
    @media(max-width:560px){.st-key-recommendation_grid div[data-testid="stColumn"]{flex:0 0 100%;max-width:100%}}
    </style>""", unsafe_allow_html=True)
    directory = Path(os.environ.get("CINEMATCH_DATA_DIR", ROOT / "data" / "ml-100k"))
    series_file = Path(os.environ.get("CINEMATCH_SERIES_FILE", ROOT / "data" / "tvmaze" / "series.json"))
    metadata_file = Path(os.environ.get("CINEMATCH_METADATA_FILE", ROOT / "data" / "metadata" / "catalog.json"))
    content_file = Path(os.environ.get("CINEMATCH_CONTENT_FILE", metadata_file.parent / "content.json"))
    artifact_root = Path(os.environ.get("CINEMATCH_ARTIFACT_ROOT", ROOT))
    if not all((directory / name).exists() for name in ("u.data", "u.item")):
        st.title("🎬 CineMatch")
        st.subheader(t("setup_title"))
        st.info(t("setup"))
        st.code("python -m scripts.download_data\npython -m scripts.download_series\n"
                "python -m scripts.download_metadata\npython -m scripts.train\nstreamlit run app/streamlit_app.py", language="bash")
        return
    modern_directory = directory.parent / "ml-latest-small"
    signature = artifact_signature([directory / "u.data", directory / "u.item", series_file, metadata_file, content_file,
                                    artifact_root / "reports" / "ml_v3.json",
                                    modern_directory / "movies.csv", modern_directory / "ratings.csv",
                                    modern_directory / "links.csv",
                                    artifact_root / "models" / "expanded.npz",
                                    artifact_root / "reports" / "expanded_metrics.json",
                                    artifact_root / "models" / "full.npz",
                                    artifact_root / "reports" / "metrics.json"])
    with st.spinner(t("learning")):
        engine, report, fetched, warnings = load_runtime(str(directory), str(series_file),
                                                        str(artifact_root), signature, str(metadata_file), str(content_file))
    movies = engine.movies
    local_memory.restore(memory, engine)
    for key, default in (("ratings", {}), ("blocked", set()), ("not_seen", set()), ("watched", set()), ("watchlist", set()), ("guide_history", []), ("demo", False)):
        st.session_state.setdefault(key, default)
    st.session_state.setdefault("topic_blocked", set(st.session_state.blocked))
    st.session_state.setdefault("snoozed", set())
    try:
        profile = engine.validate_profile(st.session_state.ratings)
        blocked = {engine.normalize_id(mid) for mid in st.session_state.blocked}
        st.session_state.ratings = profile
        st.session_state.blocked = blocked
        st.session_state.topic_blocked = {engine.normalize_id(mid) for mid in st.session_state.topic_blocked} & blocked
        watched = {engine.normalize_id(mid) for mid in st.session_state.watched} | set(profile)
        st.session_state.watched = watched
        st.session_state.not_seen = {engine.normalize_id(mid) for mid in st.session_state.not_seen} - watched
        st.session_state.watchlist = {engine.normalize_id(mid) for mid in st.session_state.watchlist} - watched
    except (ValueError, TypeError):
        st.error(t("invalid_profile"))
        if st.button(t("clear"), key="clear_invalid"):
            replace_profile({}, set())
        return
    translated_count = sum(engine.metadata.translated(mid) for mid in engine.movie_ids)
    localized_only = language == "uk" and st.session_state.get("localized_only_pref", True)
    with st.sidebar:
        st.title("Ваш смак" if language == "uk" else "Your taste")
        st.caption(t("tagline"))
        st.divider()
        media = st.selectbox(t("media"), ["All", "Movie", "Series"], key="media_type",
                             index=["All", "Movie", "Series"].index(st.session_state.get("media_type", "All")),
                             format_func=lambda value: t({"All": "all", "Movie": "kind_movie",
                                                          "Series": "kind_series"}[value]))
        genres = st.multiselect(t("genres"), engine.content.genre_names, key="genres",
                                default=[g for g in st.session_state.get("genres", [])
                                         if g in engine.content.genre_names],
                                format_func=lambda value: genre_name(value, language),
                                placeholder=t("choose_genres"))
        valid_years = movies.loc[movies.year > 0, "year"]
        years = None
        if not valid_years.empty:
            first, last = int(valid_years.min()), int(valid_years.max())
            old_years = st.session_state.get("years", (first, last))
            initial_years = (max(first, min(last, old_years[0])),
                             max(first, min(last, old_years[1])))
            years = ((first, last) if first == last else
                     st.slider(t("years"), first, last, initial_years, key="years"))
        with st.expander(t("advanced")):
            algorithm = st.selectbox(t("model"), ALGORITHMS, key="algorithm",
                                     index=ALGORITHMS.index(st.session_state.get("algorithm", "Adaptive")),
                                     format_func=lambda value: model_name(value, language))
            minimum = st.select_slider(t("minimum"), [0, 1, 5, 10, 20, 50],
                                       value=st.session_state.get("minimum", 0), key="minimum")
            variety = st.slider(t("diversity"), 0.0, 1.0, st.session_state.get("diversity", 0.0),
                                .05, help=t("diversity_help"),
                                key="diversity")
        posters = st.checkbox(t("posters"), value=st.session_state.get("posters", True), key="posters")
        if language == "uk":
            if not translated_count:
                st.session_state.localized_only = False
            localized_only = st.checkbox(t("localized_only"),
                value=(st.session_state.get("localized_only", st.session_state.get("localized_only_pref", True))
                       if translated_count else False), key="localized_only", disabled=not translated_count)
            # A conditional widget is cleaned up in English; retain its preference separately.
            if translated_count:
                st.session_state.localized_only_pref = localized_only
            st.caption(t("metadata_coverage", count=translated_count, total=len(movies)))
        st.divider()
        st.metric(t("my_count"), len(profile))
        st.caption(t("library_counts", later=len(st.session_state.watchlist), seen=len(watched)))
        st.caption(t("catalog_count", films=engine.film_count, series=int(engine.is_series.sum())))
        st.caption(t("sources"))
        if st.button(t("demo"), key="demo_button", use_container_width=True):
            seeds = [("Star Wars (1977)", 5), ("Toy Story (1995)", 4),
                     ("Godfather, The (1972)", 5), ("Pulp Fiction (1994)", 4),
                     ("Fargo (1996)", 4), ("Breaking Bad (2008)", 5),
                     ("Stranger Things (2016)", 4)]
            ratings = {int(movies.loc[movies.title == title, "movie_id"].iloc[0]): value
                       for title, value in seeds if (movies.title == title).any()}
            replace_profile(ratings, set(), demo=True)
        if st.button(t("clear"), key="clear_profile", use_container_width=True):
            replace_profile({}, set())
        local_memory.controls(memory, t)

    if st.session_state.demo:
        st.info(t("demo_notice"))
    st.markdown(f'<div class="hero"><div class="eyebrow">{t("eyebrow")}</div>'
                f'<h1>{t("hero")}</h1><p>{t("hero_detail")}</p></div>', unsafe_allow_html=True)
    for warning in warnings:
        st.warning(t(warning))
    if not engine.is_series.any():
        st.info(t("series_missing"))
    filters = dict(blocked=blocked, genres=genres, year_range=years, min_ratings=minimum,
                   media_type=media, diversity=variety, language=language, localized_only=localized_only, watched=watched,
                   topic_blocked=st.session_state.topic_blocked, snoozed=st.session_state.snoozed)
    for_you, library, ml = st.tabs([t("for_you"), t("library"), "ML Lab"])
    with for_you:
        guided, discover = st.tabs([t("guided"), t("discover")])
    with library:
        later_tab, saved = st.tabs([t("watchlist"), t("my_ratings")])
    with ml:
        lab, compare, archive = st.tabs([t("ml_live"), t("compare"), t("ml_archive")])
    if not translated_count:
        st.info(t("metadata_missing"))

    def poster(url, title, guide=False):
        if posters and url:
            safe_url, safe_title = html.escape(url, quote=True), html.escape(title, quote=True)
            cls = "poster guide-poster" if guide else "poster"
            st.markdown(f'<img class="{cls}" src="{safe_url}" alt="{safe_title}" loading="lazy">', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="poster-missing"><span>🎞</span><p>{t("no_poster") if posters else t("posters_hidden")}</p></div>', unsafe_allow_html=True)

    def remember_change():
        profile_actions.remember_change(st.session_state)

    def content_details(mid):
        if engine.semantic is None:
            return
        item = engine.semantic.items[mid]
        summary = item["summary_uk"] if language == "uk" else item["summary_en"]
        if not summary and language == "uk":
            summary = item["summary_en"]
            if summary:
                st.caption(t("original_summary"))
        st.write(summary or t("missing_summary"))
        source = item["source_uk"] if language == "uk" and item["summary_uk"] else item["source_url"]
        if summary and source:
            st.link_button(t("source_summary") + " · CC BY-SA", source)

    def rate_title(mid, value):
        profile_actions.rate_title(st.session_state, mid, value)

    def watchlist_button(mid, prefix):
        saved_later = mid in st.session_state.watchlist
        label = t("watchlist_saved" if saved_later else "watchlist_add")
        if st.button(label, key=f"later_{prefix}_{mid}", use_container_width=True):
            if saved_later:
                st.session_state.watchlist.remove(mid)
            else:
                st.session_state.watchlist.add(mid)
            st.rerun()

    def mark_seen(mid, origin):
        profile_actions.mark_seen(st.session_state, mid, origin)
        st.rerun()

    def seen_feedback(origin):
        previous = st.session_state.get("pending_seen")
        if not previous or previous["origin"] != origin:
            return
        with st.container(border=True):
            seen_options(previous)

    def seen_options(previous):
        mid = previous["mid"]
        st.caption(t("seen_rate_title"))
        st.subheader(engine.display_title(mid, language))
        st.write(t("seen_rate_note"))
        for value, column in enumerate(st.columns(5), 1):
            if column.button(f"{value} ★", key=f"seen_rate_{mid}_{value}", use_container_width=True):
                rate_title(mid, value)
                st.session_state.pop("pending_seen", None)
                st.rerun()
        if st.button(t("seen_no_rating"), key="seen_no_rating", use_container_width=True):
            st.session_state.pop("pending_seen", None)
            st.rerun()
        if st.button(t("seen_cancel"), key="seen_cancel", use_container_width=True):
            profile_actions.cancel_seen(st.session_state)
            st.rerun()

    with guided:
        st.caption(t("guide_detail"))
        if len(profile) >= 5:
            st.caption(t("guide_ready"))
        else:
            st.progress(len(profile) / 5, text=t("guide_progress", count=len(profile)))
        queue = discovery_queue(engine, profile, st.session_state.not_seen, blocked, media, localized_only, watched=watched)
        if queue:
            mid = queue[0]
            row = movies.iloc[engine.positions[mid]]
            result = engine._result(engine.positions[mid], 0, {}, "Popularity", language)
            with st.container(border=True, key="guided_card"):
                cover, answer = st.columns([1, 1.65], gap="large")
                with cover:
                    poster(result.poster_url, result.title, guide=True)
                with answer:
                    st.markdown(f'<p class="kind">{t("kind_series" if mid < 0 else "kind_movie")}</p>', unsafe_allow_html=True)
                    st.subheader(result.title)
                    if language == "uk" and engine.metadata.translated(mid):
                        st.caption(t("original", title=row.title))
                    st.write(" · ".join(genre_name(g, language) for g in row.genres))
                    st.write(t("guide_heading"))
                    buttons = st.columns(5)
                    for value, column in enumerate(buttons, 1):
                        if column.button(f"{value} ★", key=f"guide_rate_{value}", use_container_width=True,
                                         help=t("rating_hint")):
                            st.session_state.guide_history.append((mid, "rating", value, mid in st.session_state.watchlist))
                            rate_title(mid, value)
                            st.rerun()
                    if st.button(t("not_seen"), key="guide_not_seen", use_container_width=True):
                        st.session_state.guide_history.append((mid, "not_seen", None))
                        st.session_state.not_seen.add(mid)
                        st.rerun()
                    watchlist_button(mid, "guide")
                    st.caption(t("guide_hint"))
                    with st.expander(t("source_link")):
                        content_details(mid)
                        if result.image_source:
                            st.link_button(t("image_credits"), result.image_source)
                        if language == "uk" and engine.metadata.translated(mid):
                            source = engine.metadata.items[mid]["title_source"]
                            if source:
                                st.link_button(t("title_credits"), source)
        else:
            st.info(t("guide_empty"))
        if st.session_state.guide_history and st.button(t("undo"), key="guide_undo"):
            profile_actions.undo_guide(st.session_state)
            st.rerun()
        if st.session_state.not_seen:
            st.caption(t("not_seen_note", count=len(st.session_state.not_seen)))
            if st.button(t("guide_reset"), key="guide_reset"):
                st.session_state.not_seen = set()
                st.session_state.guide_history = []
                st.rerun()
        st.caption(t("guide_all"))
    with discover:
        with st.expander(t("search_heading")):
            query = st.text_input(t("search"), value=st.session_state.get("query", ""),
                                  placeholder=t("search_placeholder"), key="query")
            # Literal search finds the whole catalog, including watched titles.
            available = (movies if query.strip() else movies[~movies.movie_id.isin(watched)]).copy()
            if localized_only:
                available = available[available.movie_id.map(engine.metadata.translated)]
            if media != "All":
                available = available[available.media_type == media]
            if query.strip():
                available["uk_title"] = available.movie_id.map(lambda mid: engine.display_title(mid, "uk"))
                available = available[available.apply(lambda row: title_matches(query.strip(),
                    row.title, row.uk_title, getattr(row, "alternate_title", ""),
                    *engine.metadata.items.get(int(row.movie_id), {}).get("search_aliases", [])), axis=1)]
            else:
                quality = dict(zip(engine.movie_ids, engine.score_components({})["Popularity"]))
                available = available.assign(quality=available.movie_id.map(quality)).sort_values(
                    ["quality", "movie_id"], ascending=[False, True])
            choices = available.movie_id.head(80).tolist()
            if choices:
                def title_label(mid):
                    kind = t("kind_series" if mid < 0 else "kind_movie")
                    seen_label = f" · {t('seen')}" if mid in watched else ""
                    return f"{engine.display_title(mid, language)} · {kind}{seen_label}"
    
                with st.form("rate_movie"):
                    left, right = st.columns([3, 1])
                    with left:
                        item_id = st.selectbox(t("choose"), choices, format_func=title_label, key="rate_id")
                    with right:
                        rating = st.slider(t("your_rating"), .5, 5.0, 4.0, .5, key="rate_value")
                    if st.form_submit_button(t("save_rating"), type="primary"):
                        rate_title(int(item_id), rating)
                        st.rerun()
            else:
                st.caption(t("no_search"))
            st.caption(t("rating_hint"))
        st.divider()
        intent_query = st.text_input(t("semantic_search"), placeholder=t("semantic_placeholder"), key="intent_query",
                                    disabled=engine.semantic is None)
        if intent_query and engine.semantic is not None:
            if engine.semantic.query_scores(intent_query) is None:
                st.info(t("intent_no_words"))
            filters["query"] = intent_query
        st.subheader(t("next_ten"))
        st.caption(t("community_start") if not profile else
                   t("taste_signals", algorithm=model_name(algorithm, language), count=len(profile)))
        seen_feedback("rec")
        if blocked:
            st.caption(t("interest_note", count=len(blocked)))
        previous_interest = st.session_state.get("last_uninterested")
        if previous_interest:
            if st.button(t("interest_undo"), key="interest_undo"):
                remember_change()
                mid, was_saved = st.session_state.pop("last_uninterested")[:2]
                st.session_state.blocked.discard(mid)
                st.session_state.topic_blocked.discard(mid)
                st.session_state.snoozed.discard(mid)
                if was_saved:
                    st.session_state.watchlist.add(mid)
                st.rerun()
        interest_mode = st.radio(t("interest_choose"), ["topic", "title", "now"],
                                 format_func=lambda v: t({"topic": "interest_topic", "title": "interest_specific", "now": "interest_temporary"}[v]),
                                 horizontal=True, help=t("interest_help"), key="interest_mode")
        results = engine.recommend(profile, algorithm, **filters)
        if not results:
            st.info(t("no_results"))
        with st.container(key="recommendation_grid"):
            for index, result in enumerate(results):
                if index % 3 == 0:
                    columns = st.columns(3)
                with columns[index % 3], st.container(border=True):
                    poster(result.poster_url, result.title)
                    st.caption(t("kind_series" if result.media_type == "Series" else "kind_movie"))
                    st.subheader(result.title)
                    st.caption(" · ".join(genre_name(g, language) for g in result.genres))
                    with st.expander(t("details")):
                        st.write(result.reason)
                        content_details(result.movie_id)
                        if engine.semantic is not None and profile and algorithm in ("Semantic", "Adaptive"):
                            evidence = engine.semantic.evidence(profile, result.movie_id)
                            if evidence and evidence["terms"]:
                                st.caption(t("evidence_seed", title=engine.display_title(evidence["seed"], language)))
                                st.caption(" · ".join(evidence["terms"]))
                                st.caption(t("evidence_note"))
                    if result.average_rating is None:
                        st.caption(t("unrated"))
                    elif result.media_type == "Series":
                        st.caption(t("tv_rating", rating=result.average_rating))
                    else:
                        st.caption(t("movie_rating", rating=result.average_rating, count=result.rating_count))
                    if result.image_source:
                        st.link_button(t("image_credits"), result.image_source)
                    with st.expander(t("source_link")):
                        st.link_button(result.source, result.source_url)
                    watchlist_button(result.movie_id, "rec")
                    if st.button(t("seen"), key=f"seen_rec_{result.movie_id}", use_container_width=True):
                        mark_seen(result.movie_id, "rec")
                    if st.button(t("hide"), key=f"hide_{result.movie_id}", use_container_width=True):
                        remember_change()
                        st.session_state.last_uninterested = (result.movie_id, result.movie_id in st.session_state.watchlist, interest_mode)
                        if interest_mode == "now":
                            st.session_state.snoozed.add(result.movie_id)
                        else:
                            st.session_state.blocked.add(result.movie_id)
                            st.session_state.watchlist.discard(result.movie_id)
                            if interest_mode == "topic":
                                st.session_state.topic_blocked.add(result.movie_id)
                        st.rerun()
        if results:
            export = pd.DataFrame([asdict(row) for row in results])
            export["genres"] = export.genres.map(lambda values: "|".join(values))
            st.download_button(t("download_recs"), export.to_csv(index=False),
                               file_name="cinematch-recommendations.csv", mime="text/csv")
        st.caption(t("art_note"))
        st.caption(t("tv_note"))

    with later_tab:
        st.subheader(t("watchlist_heading"))
        st.caption(t("watchlist_note"))
        seen_feedback("later")
        later_ids = sorted(st.session_state.watchlist, key=lambda mid: engine.display_title(mid, language).casefold())
        if not later_ids:
            st.info(t("watchlist_empty"))
        for index, mid in enumerate(later_ids):
            if index % 3 == 0:
                columns = st.columns(3)
            row = movies.iloc[engine.positions[mid]]
            with columns[index % 3], st.container(border=True):
                poster(engine.metadata.poster(row), engine.display_title(mid, language))
                st.caption(t("kind_series" if mid < 0 else "kind_movie"))
                st.subheader(engine.display_title(mid, language))
                st.caption(" · ".join(genre_name(g, language) for g in row.genres))
                if st.button(t("seen"), key=f"seen_later_{mid}", use_container_width=True):
                    mark_seen(mid, "later")
                if st.button(t("watchlist_remove"), key=f"remove_later_{mid}", use_container_width=True):
                    st.session_state.watchlist.remove(mid)
                    st.rerun()
                image_source = engine.metadata.image_source(row)
                if image_source:
                    st.link_button(t("image_credits"), image_source)

    with saved:
        st.subheader(t("profile_heading"))
        seen_feedback("saved")
        if not profile:
            st.info(t("empty_profile"))
        for mid, value in list(profile.items()):
            row = movies.iloc[engine.positions[mid]]
            name, edit, remove = st.columns([4, 1, 1])
            with name:
                st.write(engine.display_title(mid, language))
                st.caption(" · ".join(genre_name(g, language) for g in row.genres))
            with edit:
                changed = st.number_input(t("your_rating"), .5, 5.0, float(value), .5,
                                          key=f"edit_{mid}")
                if changed != value:
                    remember_change()
                    st.session_state.ratings[mid] = changed
                    st.rerun()
            with remove:
                if st.button(t("remove"), key=f"remove_{mid}"):
                    remember_change()
                    del st.session_state.ratings[mid]
                    del st.session_state[f"edit_{mid}"]
                    st.rerun()
        unrated_seen = watched - set(profile)
        if unrated_seen:
            with st.expander(t("seen_history")):
                st.caption(t("seen_history_note"))
                for mid in sorted(unrated_seen):
                    name_col, rate_col, restore_col = st.columns([3, 1, 2])
                    name_col.write(engine.display_title(mid, language))
                    if rate_col.button(t("seen_rate"), key=f"rate_seen_{mid}"):
                        mark_seen(mid, "saved")
                    if restore_col.button(t("seen_restore"), key=f"restore_seen_{mid}"):
                        remember_change()
                        st.session_state.watched.remove(mid)
                        st.rerun()
        if blocked:
            st.caption(t("hidden_count", count=len(blocked)))
            with st.expander(t("interest_history")):
                st.caption(t("interest_detail"))
                for mid in sorted(blocked):
                    title_col, restore_col = st.columns([3, 1])
                    title_col.write(engine.display_title(mid, language))
                    if restore_col.button(t("interest_restore"), key=f"restore_interest_{mid}"):
                        remember_change()
                        st.session_state.blocked.discard(mid)
                        st.session_state.topic_blocked.discard(mid)
                        st.rerun()
            if st.button(t("restore"), key="restore_hidden"):
                remember_change()
                st.session_state.blocked = set()
                st.session_state.topic_blocked = set()
                st.rerun()
        positive, negative = engine.content.signals(profile)
        with st.expander(t("signals")):
            for heading, values in (("positive", positive), ("negative", negative)):
                st.write(t(heading))
                st.write(", ".join(f"{genre_name(g, language)} ({weight:+.2f})"
                                   for g, weight in values) or t("no_signal"))
            st.caption(t("signal_note"))
            if blocked:
                st.caption(t("interest_note", count=len(blocked)))
        payload = export_profile(engine, profile, blocked, st.session_state.not_seen,
                                 watched, st.session_state.watchlist, st.session_state.topic_blocked)
        st.download_button(t("export"), payload, file_name="cinematch-profile.json",
                           mime="application/json")
        uploaded = st.file_uploader(t("import"), type=["json"], key="profile_upload")
        if uploaded is not None and st.button(t("apply_import"), key="apply_import"):
            try:
                imported, hidden, not_seen, seen, later = import_library_profile(engine, uploaded.getvalue())
                topics = import_topics(engine, uploaded.getvalue())
            except (ValueError, TypeError, UnicodeError):
                st.error(t("invalid_profile"))
            else:
                replace_profile(imported, hidden, not_seen=not_seen, watched=seen, watchlist=later, topic_blocked=topics)
        if os.environ.get("CINEMATCH_LOCAL_PROFILES", "1") == "1":
            st.divider()
            st.subheader(t("local_save_heading"))
            store = ProfileStore(os.environ.get("CINEMATCH_PROFILE_DB",
                                                ROOT / "data" / "profiles.sqlite3"))
            name = st.text_input(t("local_name"), value=st.session_state.get("profile_name", ""),
                                 key="profile_name")
            try:
                if st.button(t("local_save"), key="save_local"):
                    try:
                        store.save(name, payload)
                    except ValueError:
                        st.error(t("save_failed"))
                    else:
                        st.success(t("saved_ok"))
                names = store.names()
                if names:
                    chosen = st.selectbox(t("saved_profile"), names, key="saved_name")
                    if st.button(t("local_load"), key="load_local"):
                        try:
                            saved_payload = store.load(chosen)
                            imported, hidden, not_seen, seen, later = import_library_profile(engine, saved_payload)
                            topics = import_topics(engine, saved_payload)
                        except (ValueError, TypeError, UnicodeError):
                            st.error(t("invalid_profile"))
                        else:
                            replace_profile(imported, hidden, not_seen=not_seen, watched=seen, watchlist=later, topic_blocked=topics)
            except (OSError, sqlite3.Error):
                st.error(t("storage_failed"))
            st.caption(t("local_note"))
    with compare:
        st.subheader(t("compare_heading"))
        left, right = st.columns(2)
        models = []
        for column, key, initial in ((left, "left_model", 0), (right, "right_model", 1)):
            with column:
                models.append(st.selectbox(t(key), ALGORITHMS,
                                            index=ALGORITHMS.index(st.session_state.get(key, ALGORITHMS[initial])),
                                            key=key,
                                            format_func=lambda value: model_name(value, language)))
        lists = [engine.recommend(profile, model, **filters) for model in models]
        shared = {row.movie_id for row in lists[0]} & {row.movie_id for row in lists[1]}
        st.caption(t("overlap", count=len(shared)))
        for column, results in zip(st.columns(2), lists):
            with column:
                for position, result in enumerate(results, 1):
                    st.write(f"**{position}. {result.title}**")
                    if result.movie_id in shared:
                        st.caption(t("shared"))
                    st.caption(result.reason)
                if not results:
                    st.info(t("no_results"))
    with lab:
        from app.ml_lab import render
        render(engine, profile, algorithm, filters, t, language)
    with archive:
        st.subheader(t("lab_heading"))
        st.write(t("lab_detail"))
        if report:
            metrics = pd.DataFrame.from_dict(report["metrics"], orient="index")
            metrics.index = [model_name(model, language) for model in metrics.index]
            metrics = metrics.rename(columns={"coverage": t("coverage"), "diversity": t("diversity_metric")})
            st.dataframe(metrics.style.format("{:.4f}"), use_container_width=True)
            st.bar_chart(metrics[["ndcg@10"]], color="#e84f3e")
            detail = report["test_cohort"]
            st.caption(t("benchmark_scope", users=detail["evaluated_users"], alpha=report["selected_alpha"]))
            winner = max(report["metrics"], key=lambda model: report["metrics"][model]["ndcg@10"])
            st.info(t("best_model", model=model_name(winner, language)))
            with st.expander(t("uncertainty")):
                intervals = [{t("model"): model_name(model, language), "NDCG@10":
                              f"{values['ndcg@10'][0]:.4f} – {values['ndcg@10'][1]:.4f}"}
                             for model, values in report["confidence_95"].items()]
                st.dataframe(pd.DataFrame(intervals), hide_index=True, use_container_width=True)
                st.caption(t("interval_note"))
            with st.expander(t("onboarding")):
                table = pd.DataFrame(report["onboarding"]["results"])
                if not table.empty:
                    table["algorithm"] = table.algorithm.map(lambda model: model_name(model, language))
                    table = table.rename(columns={"seed_ratings": t("seed_count"), "algorithm": t("model"),
                                                  "coverage": t("coverage"), "diversity": t("diversity_metric")})
                    st.dataframe(table, hide_index=True, use_container_width=True)
                st.caption(t("onboarding_note"))
            with st.expander(t("diversity_lab")):
                table = pd.DataFrame(report["diversity_analysis"]).rename(columns={
                    "weight": t("diversity"), "coverage": t("coverage"), "diversity": t("diversity_metric")})
                st.dataframe(table, hide_index=True,
                             use_container_width=True)
                st.caption(t("diversity_lab_note"))
            with st.expander(t("limitations")):
                st.write(t("limit_detail"))
        else:
            st.info(t("benchmark_missing"))
    st.caption(t("tv_credits"))
    st.link_button("TVmaze API · CC BY-SA", "https://www.tvmaze.com/api#licensing")
    if fetched:
        st.caption(t("updated", date=fetched[:10]))


