"""Persist changes even when a UI action requests an immediate Streamlit rerun."""

import json
import os
import sqlite3
from pathlib import Path

import streamlit as st

from src.i18n import tr
from src.memory import MemoryConflict, MemoryStore, preferences
from src.profiles import export_profile, import_library_profile, import_topics


def initialize(root):
    if (os.environ.get("CINEMATCH_LOCAL_PROFILES", "1") != "1"
            or os.environ.get("CINEMATCH_AUTOSAVE", "1") != "1"):
        return None
    store = MemoryStore(os.environ.get("CINEMATCH_PROFILE_DB", Path(root) / "data" / "profiles.sqlite3"))
    if "_memory_initialized" not in st.session_state:
        st.session_state._memory_initialized = True
        try:
            revision, document = store.read()
        except (OSError, sqlite3.Error, ValueError, UnicodeError):
            st.session_state._memory_error = "memory_failed"
        else:
            st.session_state._memory_revision = revision
            st.session_state._memory_document = document
            st.session_state.autosave = document["enabled"] if document else True
            if document and document["enabled"]:
                for key, value in preferences(document["preferences"]).items():
                    st.session_state[key] = value
                st.session_state._memory_pending = document["profile"]
    return {"store": store, "ready": False}


def restore(memory, engine):
    if memory is None or st.session_state.get("_memory_error"):
        return
    payload = st.session_state.pop("_memory_pending", None)
    if payload is not None:
        try:
            ratings, blocked, not_seen, watched, watchlist = import_library_profile(engine, payload)
            topics = import_topics(engine, payload)
        except (ValueError, TypeError, UnicodeError):
            st.session_state._memory_error = "memory_failed"
            return
        for key, value in zip(("ratings", "blocked", "not_seen", "watched", "watchlist"),
                              (ratings, blocked, not_seen, watched, watchlist)):
            st.session_state[key] = value
        st.session_state.topic_blocked = topics
    memory.update(ready=True, engine=engine)


def save(memory):
    if memory is None or not memory["ready"] or st.session_state.get("_memory_error"):
        return
    if st.session_state.get("demo", False):
        return
    try:
        enabled = st.session_state.get("autosave", True)
        payload = export_profile(memory["engine"], st.session_state.ratings, st.session_state.blocked,
                                 st.session_state.not_seen, st.session_state.watched, st.session_state.watchlist,
                                 st.session_state.get("topic_blocked", st.session_state.blocked))
        document = {"version": 1, "enabled": enabled, "profile": payload if enabled else "",
                    "preferences": preferences(st.session_state) if enabled else {}}
        document = json.loads(json.dumps(document))
        if document != st.session_state.get("_memory_document"):
            revision = memory["store"].write(document, st.session_state.get("_memory_revision", 0))
            st.session_state._memory_revision = revision
            st.session_state._memory_document = document
    except MemoryConflict:
        st.session_state._memory_error = "memory_conflict"
    except (OSError, sqlite3.Error, ValueError, TypeError, UnicodeError):
        st.session_state._memory_error = "memory_failed"
    if st.session_state.get("_memory_error"):
        with st.sidebar:
            st.warning(tr(st.session_state._memory_error, st.session_state.get("ui_language", "uk")))


def controls(memory, t):
    if memory is None:
        st.caption(t("session"))
        return
    st.checkbox(t("autosave"), key="autosave", value=st.session_state.get("autosave", True),
                disabled=bool(st.session_state.get("_memory_error")))
    if st.session_state.get("_memory_error"):
        st.warning(t(st.session_state._memory_error))
    else:
        st.caption(t("autosave_note" if st.session_state.get("autosave", True) else "autosave_off"))
