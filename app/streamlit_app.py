"""Small resilient entry point: keep failures out of the public interface."""

import importlib
import logging
import os
import sys
import uuid
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def maintenance_active():
    flag = Path(os.environ.get("CINEMATCH_MAINTENANCE_FILE",
                               ROOT / "data" / "runtime" / "maintenance.flag"))
    return os.environ.get("CINEMATCH_MAINTENANCE") == "1" or flag.is_file()


def notice(maintenance=False, reference=None):
    language = st.session_state.get("ui_language", os.environ.get("CINEMATCH_DEFAULT_LANGUAGE", "uk"))
    uk = language == "uk"
    st.title("🎬 CineMatch")
    if maintenance:
        st.subheader("Ведуться технічні роботи" if uk else "Maintenance in progress")
        st.info("Ми оновлюємо CineMatch. Будь ласка, завітайте трохи пізніше." if uk else
                "We are updating CineMatch. Please check back shortly.")
    else:
        st.subheader("Сервіс тимчасово недоступний" if uk else "Temporarily unavailable")
        st.info("Не вдалося відкрити цю сторінку. Спробуйте ще раз трохи пізніше." if uk else
                "We could not open this page. Please try again shortly.")
        st.caption(("Код звернення: " if uk else "Reference: ") + reference)
    if st.button("Спробувати ще раз" if uk else "Try again", key="service_retry"):
        st.rerun()


def safe_main(load_ui=None):
    st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide")
    st.set_option("client.showErrorDetails", False)
    if maintenance_active():
        notice(maintenance=True)
        return
    surface = st.empty()
    try:
        # Imports belong inside the boundary so import errors are covered too.
        module = "app.interface" if os.environ.get("CINEMATCH_UI") == "classic" else "app.product_ui"
        ui = (load_ui or (lambda: importlib.import_module(module)))()
        with surface.container():
            ui.main()
    except Exception:
        reference = uuid.uuid4().hex[:8]
        logging.getLogger("cinematch").exception("CineMatch incident %s", reference)
        surface.empty()
        st.sidebar.empty()
        with surface.container():
            notice(reference=reference)


if __name__ == "__main__":
    safe_main()
