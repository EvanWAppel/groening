"""TDD for the read-only JSON serving layer (E8) over the DuckDB marts.

The API is a thin, read-only window onto the dbt-built ``mart_*`` tables. These
tests run against a tiny throwaway DuckDB (built in ``tmp_path``) injected via the
``get_connection`` dependency override, so they never touch the real 47MB warehouse
and never depend on live data.
"""

import duckdb
import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def warehouse(tmp_path):
    """A minimal warehouse: two marts, plus a raw table and a staging view that
    the API must NOT expose (only ``main.mart_*`` base tables are served)."""
    path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE TABLE main.mart_weather_annual (year INTEGER, avg_temp DOUBLE, note VARCHAR)"
    )
    con.execute(
        "INSERT INTO main.mart_weather_annual VALUES "
        "(2024, 54.5, 'wet'), (2025, 55.1, NULL), (2026, 53.9, 'wetter')"
    )
    con.execute("CREATE TABLE main.mart_parks (name VARCHAR, acres DOUBLE)")
    con.execute("INSERT INTO main.mart_parks VALUES ('Forest Park', 5200.0)")
    # None of these should ever surface through the API.
    con.execute("CREATE TABLE raw.weather (x INTEGER)")
    con.execute("CREATE VIEW main.stg_weather AS SELECT * FROM main.mart_weather_annual")
    # 'martini' would match an UNESCAPED LIKE 'mart_%' (the '_' as any-char wildcard);
    # it must NOT match the escaped 'mart\_%'. Guards against a dropped ESCAPE clause.
    con.execute("CREATE TABLE main.martini (proof INTEGER)")
    con.close()
    return duckdb.connect(str(path), read_only=True)


@pytest.fixture
def client(warehouse):
    api.app.dependency_overrides[api.get_connection] = lambda: warehouse
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


class TestHealth:
    def test_ok_and_reports_mart_count(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["marts"] == 2


class TestListMarts:
    def test_lists_only_marts_sorted_with_row_counts(self, client):
        r = client.get("/marts")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 2
        names = [m["name"] for m in body["marts"]]
        # sorted; excludes raw.*, stg_* views, and 'martini' (escaped '_' is literal)
        assert names == ["mart_parks", "mart_weather_annual"]
        rows_by_name = {m["name"]: m["rows"] for m in body["marts"]}
        assert rows_by_name == {"mart_parks": 1, "mart_weather_annual": 3}

    def test_underscore_in_prefix_is_literal_not_wildcard(self, client):
        # 'martini' matches an unescaped LIKE 'mart_%' but must be excluded.
        assert client.get("/marts/martini").status_code == 404


class TestMartRows:
    def test_returns_rows_with_total_and_null_preserved(self, client):
        r = client.get("/marts/mart_weather_annual")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "mart_weather_annual"
        assert body["total"] == 3
        assert body["count"] == 3
        assert body["rows"][0] == {"year": 2024, "avg_temp": 54.5, "note": "wet"}
        assert body["rows"][1]["note"] is None  # SQL NULL -> JSON null

    def test_limit_and_offset_paginate(self, client):
        r = client.get("/marts/mart_weather_annual", params={"limit": 1, "offset": 1})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3  # total is the full count, not the page
        assert body["count"] == 1
        assert body["limit"] == 1
        assert body["offset"] == 1
        assert body["rows"] == [{"year": 2025, "avg_temp": 55.1, "note": None}]

    def test_unknown_mart_is_404(self, client):
        r = client.get("/marts/mart_does_not_exist")
        assert r.status_code == 404

    def test_raw_table_is_not_reachable(self, client):
        assert client.get("/marts/weather").status_code == 404

    def test_staging_view_is_not_reachable(self, client):
        assert client.get("/marts/stg_weather").status_code == 404

    def test_sql_injection_name_is_rejected(self, client):
        r = client.get("/marts/mart_weather_annual; DROP TABLE main.mart_parks")
        assert r.status_code == 404
        # And the table is still there afterwards.
        assert client.get("/marts").json()["count"] == 2

    def test_offset_past_end_returns_empty_page_with_full_total(self, client):
        r = client.get("/marts/mart_weather_annual", params={"offset": 100})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert body["count"] == 0
        assert body["rows"] == []

    def test_integer_column_stays_integer_not_float(self, client):
        # Native fetchall (not the pandas roundtrip) keeps 2024 an int, not 2024.0.
        row = client.get("/marts/mart_weather_annual").json()["rows"][0]
        assert row["year"] == 2024
        assert isinstance(row["year"], int)

    def test_limit_over_max_is_rejected(self, client):
        assert client.get("/marts/mart_weather_annual", params={"limit": 10001}).status_code == 422

    def test_limit_zero_is_rejected(self, client):
        assert client.get("/marts/mart_weather_annual", params={"limit": 0}).status_code == 422

    def test_negative_offset_is_rejected(self, client):
        assert client.get("/marts/mart_weather_annual", params={"offset": -1}).status_code == 422


class TestCatalogPinning:
    def test_attached_catalog_marts_do_not_leak(self, tmp_path):
        # A second DB with its own main.mart_evil, ATTACHed to our connection, must
        # never surface: list_marts is pinned to current_database(), not just schema.
        ours = tmp_path / "ours.duckdb"
        con = duckdb.connect(str(ours))
        con.execute("CREATE TABLE main.mart_ours (x INTEGER)")
        con.close()

        other = tmp_path / "other.duckdb"
        con2 = duckdb.connect(str(other))
        con2.execute("CREATE TABLE main.mart_evil (x INTEGER)")
        con2.close()

        con = duckdb.connect(str(ours), read_only=True)
        con.execute(f"ATTACH '{other}' AS other (READ_ONLY)")
        assert api.list_marts(con) == ["mart_ours"]  # not mart_evil
        con.close()


class TestMartSchema:
    def test_returns_ordered_columns_with_types(self, client):
        r = client.get("/marts/mart_weather_annual/schema")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "mart_weather_annual"
        cols = [(c["name"], c["type"]) for c in body["columns"]]
        assert cols == [("year", "INTEGER"), ("avg_temp", "DOUBLE"), ("note", "VARCHAR")]

    def test_unknown_mart_schema_is_404(self, client):
        assert client.get("/marts/nope/schema").status_code == 404
