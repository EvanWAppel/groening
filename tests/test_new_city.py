"""TDD for the `make new-city` scaffold generator (TASKS E6).

Each test stamps a fresh skeleton into ``tmp_path`` and checks the result: the
expected files land, the stub ``city_config.py`` imports and honours the catalog
contract, the generic engine is copied verbatim from Groening, and nothing
Portland-specific leaks into the new metro.
"""

import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import build_warehouse
import new_city

ARGS = {"codename": "robbins", "city": "Seattle, WA", "db": "seattle"}

EXPECTED_FILES = {
    "city_config.py",
    "build_warehouse.py",
    "app_db.py",
    "streamlit_app.py",
    "views/overview.py",
    "dbt_project.yml",
    "profiles.yml",
    "models/staging/sources.yml",
    "models/staging/stg_build_metadata.sql",
    "models/marts/mart_build_metadata.sql",
    "tests/test_city_config.py",
    "Dockerfile",
    "pyproject.toml",
    "requirements.txt",
    ".gitignore",
    ".python-version",
    "README.md",
    "BLOCKED.md",
}


def _load(path: Path, name: str):
    """Import a stamped module by file path under a unique module name."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def stamped(tmp_path, monkeypatch) -> Path:
    dest = tmp_path / "robbins"
    new_city.scaffold(dest, **ARGS)
    # The stamped build_warehouse does `import city_config`; resolve it to the stub.
    monkeypatch.syspath_prepend(str(dest))
    monkeypatch.delitem(sys.modules, "city_config", raising=False)
    return dest


class TestScaffoldFiles:
    def test_stamps_the_expected_skeleton(self, stamped):
        written = {p.relative_to(stamped).as_posix() for p in stamped.rglob("*") if p.is_file()}
        assert EXPECTED_FILES <= written

    def test_no_template_placeholder_survives(self, stamped):
        for path in stamped.rglob("*"):
            if path.is_file():
                assert not re.search(r"__[A-Z][A-Z_]*__", path.read_text()), path

    def test_nothing_portland_specific_leaks(self, stamped):
        # The engine helpers are copied verbatim (their docstrings may cite the
        # Portland quirk that motivated them); everything else must be city-neutral.
        for path in stamped.rglob("*"):
            if path.is_file():
                text = path.read_text()
                for name in new_city.ENGINE_FUNCTIONS if path.name == "build_warehouse.py" else ():
                    text = text.replace(new_city.function_source(text, name), "")
                for word in ("portland", "willamette", "multnomah", "trimet"):
                    assert word not in text.lower(), f"{word!r} leaked into {path.name}"

    def test_names_are_threaded_through_dbt_and_the_app(self, stamped):
        project = yaml.safe_load((stamped / "dbt_project.yml").read_text())
        assert project["name"] == project["profile"] == "robbins"
        assert "robbins" in project["models"]
        profile = yaml.safe_load((stamped / "profiles.yml").read_text())
        assert profile["robbins"]["outputs"]["dev"]["path"] == "seattle.duckdb"
        sources = yaml.safe_load((stamped / "models/staging/sources.yml").read_text())
        assert sources["sources"][0]["database"] == "seattle"
        assert '"seattle.duckdb"' in (stamped / "app_db.py").read_text()
        assert '"seattle.duckdb"' in (stamped / "build_warehouse.py").read_text()
        assert "Seattle, WA" in (stamped / "streamlit_app.py").read_text()

    def test_every_stamped_python_file_parses(self, stamped):
        for path in stamped.rglob("*.py"):
            ast.parse(path.read_text(), filename=str(path))

    def test_stamped_project_is_ruff_clean(self, stamped):
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--no-cache", "--isolated", str(stamped)],
            capture_output=True,
            check=False,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr


    def test_stamped_project_test_suite_passes(self, stamped):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=stamped,
            capture_output=True,
            check=False,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr


class TestStubCityConfig:
    def test_stub_imports_with_an_empty_catalog(self, stamped):
        cfg = _load(stamped / "city_config.py", "stub_city_config")
        assert cfg.CITY_NAME == "Seattle, WA"
        assert cfg.SOURCES == {}
        assert cfg.DROPPED_TOPICS == {}
        assert cfg.PAGE_SIZE > 0
        assert "robbins" in cfg.USER_AGENT["User-Agent"]

    def test_stub_catalog_contract_matches_groening(self, stamped):
        cfg = _load(stamped / "city_config.py", "stub_city_config")
        assert cfg.source_catalog_rows({}) == []
        with pytest.raises(KeyError, match="undocumented_table"):
            cfg.source_catalog_rows({"undocumented_table": 3})


class TestStampedEngine:
    def test_generic_helpers_are_copied_verbatim(self, stamped):
        groening_src = Path(build_warehouse.__file__).read_text()
        stamped_src = (stamped / "build_warehouse.py").read_text()
        for name in new_city.ENGINE_FUNCTIONS:
            assert new_city.function_source(stamped_src, name) == new_city.function_source(
                groening_src, name
            ), name

    def test_stamped_build_imports_and_refuses_to_build_nothing(self, stamped, tmp_path):
        bw = _load(stamped / "build_warehouse.py", "stub_build_warehouse")
        bw.DB_PATH = tmp_path / "empty.duckdb"
        assert bw.FETCHERS == {}
        with pytest.raises(RuntimeError, match="FETCHERS"):
            bw.main()

    def test_stamped_build_loads_registered_sources_and_provenance(self, stamped, tmp_path):
        import duckdb
        import pandas as pd

        bw = _load(stamped / "build_warehouse.py", "stub_build_warehouse")
        bw.DB_PATH = tmp_path / "one.duckdb"
        bw.FETCHERS = {"parks": lambda: pd.DataFrame({"name": ["a", "b"]})}
        bw.main()
        con = duckdb.connect(str(bw.DB_PATH), read_only=True)
        try:
            assert con.execute("select count(*) from raw.parks").fetchone() == (2,)
            assert con.execute(
                "select table_name, row_count from raw.build_metadata"
            ).fetchall() == [("parks", 2)]
        finally:
            con.close()


class TestGuards:
    def test_refuses_a_non_empty_destination(self, tmp_path):
        (tmp_path / "keep.txt").write_text("mine")
        with pytest.raises(FileExistsError):
            new_city.scaffold(tmp_path, **ARGS)
        assert (tmp_path / "keep.txt").read_text() == "mine"

    @pytest.mark.parametrize("field", ["codename", "db"])
    @pytest.mark.parametrize("bad", ["Robbins", "1robbins", "rob-bins", ""])
    def test_rejects_names_dbt_cannot_use(self, tmp_path, field, bad):
        with pytest.raises(ValueError, match=field):
            new_city.scaffold(tmp_path / "x", **{**ARGS, field: bad})
        assert not (tmp_path / "x").exists()

    def test_rejects_a_blank_city(self, tmp_path):
        with pytest.raises(ValueError, match="city"):
            new_city.scaffold(tmp_path / "x", **{**ARGS, "city": "  "})

    def test_cli_stamps_the_skeleton(self, tmp_path):
        dest = tmp_path / "cli"
        new_city.main([str(dest), "--codename", "robbins", "--city", "Seattle, WA", "--db", "seattle"])
        assert (dest / "city_config.py").is_file()


def test_makefile_exposes_new_city_target():
    makefile = (Path(new_city.__file__).parent / "Makefile").read_text()
    assert re.search(r"^new-city:", makefile, re.MULTILINE)
    assert "new_city.py" in makefile


def test_guide_documents_the_scaffold():
    guide = Path(new_city.__file__).parent / "docs" / "new-city.md"
    text = guide.read_text()
    assert "make new-city" in text
    assert "city_config.py" in text
