"""Smoke test: every page of the app renders against the built warehouse (EA-213).

``/_stcore/health`` only proves the Streamlit server is up; an exception inside a
page still shows a visitor a red error box. This loads each page through the real
router (``streamlit_app.py``) with ``AppTest`` and asserts no exception and no
``st.error``. It asserts on elements only and never reads data rows.

It needs the warehouse ``build_warehouse.py && dbt build`` produces, so it runs in
the Docker build right after that step (a broken page fails the deploy). GitHub CI
never builds the warehouse, so there it skips with a reason.
"""

import logging
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app_db import DB_PATH
from ui import TOPICS

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["views/overview.py", "views/ask.py", *(f"views/{slug}.py" for slug in TOPICS), "views/sources.py"]


def test_every_view_file_is_a_page():
    """A new file under views/ must be routed (and so smoke-tested) too."""
    on_disk = {f"views/{p.name}" for p in (ROOT / "views").glob("*.py")}
    assert on_disk == set(PAGES)


@pytest.mark.skipif(
    not DB_PATH.exists(),
    reason=f"{DB_PATH.name} not built; run `uv run python build_warehouse.py && uv run dbt build --profiles-dir .` "
    "(the Docker build runs this test after building it)",
)
@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, monkeypatch):
    # No key: the Ask page must render its notice and never call the API.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=120)
    at.run()
    if page != "views/overview.py":
        at.switch_page(page).run()
    log.info("rendered %s: %d exceptions, %d errors", page, len(at.exception), len(at.error))
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error, [e.value for e in at.error]
