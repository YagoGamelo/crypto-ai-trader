"""Catch Streamlit rendering regressions without accessing brokerage networks."""
import os

from streamlit.testing.v1 import AppTest


def test_dashboard_loads_without_credentials(monkeypatch):
    for key in ("T212_DEMO_API_KEY", "T212_DEMO_API_SECRET",
                "T212_PANEL_PASSWORD", "T212_ENABLE_DEMO_ORDERS"):
        monkeypatch.delenv(key, raising=False)
    app = AppTest.from_file("app.py", default_timeout=30).run()
    assert not app.exception, [str(exc.message) for exc in app.exception]
