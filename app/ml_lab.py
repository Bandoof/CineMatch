"""Expose measured experiments and real session ranking changes, not fake accuracy."""
import pandas as pd
import streamlit as st

from src.i18n import model_name


def render(engine, profile, algorithm, filters, t, language):
    st.subheader(t("ml_explain"))
    st.write(t("ml_method"))
    st.caption(t("learning_from"))
    if engine.semantic is not None:
        a, b, c = st.columns(3)
        a.metric(t("description_count"), int(engine.semantic.covered.sum()))
        b.metric(t("latent_dimensions"), engine.semantic.dimensions)
        c.metric(t("rating_events"), len(engine.ratings))
    weights = (engine.adaptive_weights(profile) if any(mid > 0 for mid in profile)
               else [0, .75, .25] if profile else [0, 0, 1])
    st.caption(t("mix_weights", cf=weights[0], text=weights[1], quality=weights[2]))
    st.caption(t("tv_model_scope"))
    if len(profile) >= 3:
        with st.expander(t("guided")):
            st.caption(t("guide_probe_note"))
    change = st.session_state.get("recommendation_change")
    if change is not None:
        st.subheader(t("taste_delta"))
        before_filters = dict(filters)
        before_filters.update({key: change[key] for key in ("blocked", "topic_blocked", "snoozed", "watched")})
        before = engine.recommend(change["profile"], algorithm, **before_filters)
        after = engine.recommend(profile, algorithm, **filters)
        old_ids = {r.movie_id for r in before}
        new_ids = {r.movie_id for r in after}
        st.caption(t("ranking_change", count=len(new_ids-old_ids)))
        for col, label, results in zip(st.columns(2), ("taste_before", "taste_after"), (before, after)):
            with col:
                st.write("**"+t(label)+"**")
                for pos, result in enumerate(results, 1):
                    st.write(f"{pos}. {result.title}")
        st.caption(t("change_scope"))
    else:
        st.info(t("try_feedback"))
    st.divider()
    st.subheader(t("ml_compare"))
    report = getattr(engine, "ml_report", None)
    if report is None:
        st.info(t("ml_no_report"))
        return
    st.write(t("ml_scope"))
    st.caption(t("benchmark_v3_scope", validation=report["validation_users"], test=report["test_users"], events=report["events"]))
    count = st.radio(t("seed_count"), options=[3, 5, 10], index=1, horizontal=True, key="ml_seeds")
    table = pd.DataFrame([row for row in report["results"] if row["seed_ratings"] == count]).drop(columns="seed_ratings")
    table["algorithm"] = table.algorithm.map(lambda m: model_name("Content-based" if m == "Genres" else m, language))
    table = table.rename(columns={"algorithm": t("model"), "coverage": t("coverage"), "diversity": t("diversity_metric")})
    st.dataframe(table.set_index(t("model")).style.format("{:.4f}"), use_container_width=True)
    st.bar_chart(table.set_index(t("model"))[["ndcg@10"]], color="#e84f3e")
    interval = report["paired_ndcg_vs_popularity_95"][str(count)]["Adaptive"]
    adaptive = next(row for row in report["results"] if row["seed_ratings"] == count and row["algorithm"] == "Adaptive")
    popular = next(row for row in report["results"] if row["seed_ratings"] == count and row["algorithm"] == "Popularity")
    st.write(t("paired_result", delta=adaptive["ndcg@10"]-popular["ndcg@10"], low=interval[0], high=interval[1]))
    st.info(t("evidence_positive" if interval[0] > 0 else "evidence_uncertain"))
    with st.expander(t("reproducibility")):
        st.write(t("protocol_v3"))
        st.caption(t("transfer_scope"))
        st.caption(t("metadata_time_scope"))
        st.caption("SHA-256: "+report["metadata_sha256"])
        st.download_button(t("download_experiment"), pd.DataFrame(report["results"]).to_csv(index=False),
                           file_name="cinematch-1m-experiment.csv", mime="text/csv")
