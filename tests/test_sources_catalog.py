"""TDD for the Sources & Methodology catalog (city_config.SOURCES)."""

import ast
from pathlib import Path

import pytest

import build_warehouse
import city_config as cfg


def _raw_tables_loaded_by_build() -> set[str]:
    """Every raw table main() lands, read from its load_raw(con, "<name>", ...) calls.

    GTFS members are loaded in a loop over city_config.GTFS_MEMBERS, so those are
    added explicitly. build_metadata is excluded: it is written after the row
    counts are taken, so it never appears in the provenance mart.
    """
    tree = ast.parse(Path(build_warehouse.__file__).read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    names = {
        call.args[1].value
        for call in ast.walk(main)
        if isinstance(call, ast.Call)
        and getattr(call.func, "id", None) == "load_raw"
        and isinstance(call.args[1], ast.Constant)
        and isinstance(call.args[1].value, str)
    }
    return (names | set(cfg.GTFS_MEMBERS)) - {"build_metadata"}

REQUIRED_FIELDS = {"title", "page", "publisher", "url", "coverage", "grain", "license"}


class TestSourcesCatalog:
    def test_every_entry_has_the_required_fields(self):
        for table, meta in cfg.SOURCES.items():
            missing = REQUIRED_FIELDS - set(meta)
            assert not missing, f"{table} missing {missing}"

    def test_no_field_is_blank(self):
        for table, meta in cfg.SOURCES.items():
            for field in REQUIRED_FIELDS:
                assert str(meta[field]).strip(), f"{table}.{field} is blank"

    def test_page_slugs_are_nonempty(self):
        # Page slugs are NOT unique: a topic can draw on several source tables
        # (e.g. transit_routes + transit_stops both feed the "transit" page).
        assert all(str(m["page"]).strip() for m in cfg.SOURCES.values())

    def test_multi_table_topic_shares_one_page(self):
        transit = {t: m for t, m in cfg.SOURCES.items() if t.startswith("transit_")}
        assert len(transit) >= 2
        assert {m["page"] for m in transit.values()} == {"transit"}

    def test_every_raw_table_the_build_loads_is_catalogued(self):
        # source_catalog_rows raises on an uncatalogued raw table, so a table the
        # build loads without a SOURCES entry breaks the Sources page at runtime.
        missing = _raw_tables_loaded_by_build() - set(cfg.SOURCES)
        assert not missing, f"loaded by build_warehouse.main but not in SOURCES: {missing}"

    def test_urls_are_http(self):
        for table, meta in cfg.SOURCES.items():
            assert str(meta["url"]).startswith("http"), f"{table} url not http"


class TestSourceCatalogRows:
    def test_attaches_row_counts_in_catalog_order(self):
        counts = {t: i for i, t in enumerate(cfg.SOURCES)}
        rows = cfg.source_catalog_rows(counts)
        assert [r["table"] for r in rows] == list(cfg.SOURCES)
        assert all(r["row_count"] == counts[r["table"]] for r in rows)

    def test_preserves_catalog_metadata(self):
        rows = cfg.source_catalog_rows({"parks": 316})
        parks = next(r for r in rows if r["table"] == "parks")
        assert parks["publisher"] == cfg.SOURCES["parks"]["publisher"]
        assert parks["row_count"] == 316

    def test_uncounted_table_gets_none_not_dropped(self):
        # A catalogued source with no count row still appears (row_count None),
        # so the page never silently omits a dataset.
        rows = cfg.source_catalog_rows({})
        assert len(rows) == len(cfg.SOURCES)
        assert all(r["row_count"] is None for r in rows)

    def test_undocumented_raw_table_raises(self):
        with pytest.raises(KeyError, match="missing from SOURCES"):
            cfg.source_catalog_rows({"a_new_untracked_source": 5})
