from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

def recovery_page(load_ui):
    from app.streamlit_app import safe_main
    safe_main(load_ui=load_ui)


@pytest.mark.parametrize("failure", ["import", "runtime"])
@pytest.mark.parametrize("language", ["uk", "en"])
def test_public_error_does_not_leak_details(tmp_path, monkeypatch, failure, language):
    monkeypatch.setenv("CINEMATCH_MAINTENANCE_FILE", str(tmp_path / "absent.flag"))
    monkeypatch.setenv("CINEMATCH_DEFAULT_LANGUAGE", language)

    def page():
        import streamlit as st
        st.write("Partial page should be removed")
        raise RuntimeError("private /path/to/data token=secret")

    def loader():
        if failure == "import":
            raise ImportError("private import_library_profile /path/to/profiles.py")
        return SimpleNamespace(main=page)

    app = AppTest.from_function(recovery_page, kwargs={"load_ui": loader}, default_timeout=30).run()
    assert not app.exception
    assert not app.markdown
    assert len(app.info) == 1
    assert app.subheader[0].value == ("Сервіс тимчасово недоступний" if language == "uk" else
                                      "Temporarily unavailable")
    assert "private" not in str(app)
    assert app.button(key="service_retry")


def test_maintenance_does_not_load_application(tmp_path, monkeypatch):
    flag = tmp_path / "maintenance.flag"
    flag.write_text("Updating", encoding="utf-8")
    monkeypatch.setenv("CINEMATCH_MAINTENANCE_FILE", str(flag))
    monkeypatch.setenv("CINEMATCH_DEFAULT_LANGUAGE", "uk")

    def loader():
        raise AssertionError("Maintenance must not import or load models")

    app = AppTest.from_function(recovery_page, kwargs={"load_ui": loader}, default_timeout=30).run()
    assert not app.exception
    assert app.subheader[0].value == "Ведуться технічні роботи"
    flag.unlink()
    # Rerunning sees the switch change; the protected import failure is neutral.
    app.button(key="service_retry").click().run()
    assert not app.exception
    assert app.subheader[0].value == "Сервіс тимчасово недоступний"
