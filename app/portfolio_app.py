"""Dedicated session-isolated demo entry point. It never selects the classic UI."""

import importlib
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.streamlit_app import safe_main  # noqa: E402

st.session_state._portfolio_mode = True
safe_main(load_ui=lambda: importlib.import_module("app.product_ui"))
