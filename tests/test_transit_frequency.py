"""TDD for transit service frequency (TASKS E7a follow-up).

Two layers:
- the GTFS parser config keeps trips.txt + calendar.txt (raw.transit_trips /
  raw.transit_calendar), and
- the dbt models that turn them into mart_transit_route_frequency: scheduled
  trips per route on one reference weekday, Saturday and Sunday.

The SQL is exercised for real: each model file is rendered with its
``source()``/``ref()`` calls replaced by plain relation names and run in an
in-memory DuckDB over tiny fixture raw tables.
"""

import io
import re
import zipfile
from pathlib import Path

import duckdb
import pandas as pd
import pytest

import city_config as cfg
from build_warehouse import _parse_gtfs

MODELS = Path(__file__).resolve().parent.parent / "models"

# Built on Wednesday 2026-10-21 -> reference Wed 10-21, Sat 10-24, Sun 10-25.
BUILT_AT = "2026-10-21T14:30:00+00:00"


# --------------------------------------------------------------------------- #
# Parser config                                                                #
# --------------------------------------------------------------------------- #
class TestGtfsMembersForFrequency:
    def test_trips_member_keeps_route_service_and_trip_ids(self):
        member, cols = cfg.GTFS_MEMBERS["transit_trips"]
        assert member == "trips.txt"
        assert {"route_id", "service_id", "trip_id", "direction_id"} <= set(cols)

    def test_calendar_member_keeps_day_flags_and_date_range(self):
        member, cols = cfg.GTFS_MEMBERS["transit_calendar"]
        assert member == "calendar.txt"
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        assert {"service_id", "start_date", "end_date", *days} <= set(cols)

    def test_new_raw_tables_are_catalogued_on_the_transit_page(self):
        for table in ("transit_trips", "transit_calendar"):
            assert cfg.SOURCES[table]["page"] == "transit"
            assert cfg.SOURCES[table]["url"] == cfg.TRIMET_GTFS_URL

    def test_parser_reads_trips_and_calendar_as_strings(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(
                "trips.txt",
                "﻿route_id,service_id,trip_id,trip_headsign,direction_id,block_id\n"
                "100,W1,0001,Downtown,0,b1\n100,W1,0002,Gresham,1,b1\n",
            )
            z.writestr(
                "calendar.txt",
                "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
                "start_date,end_date\nW1,1,1,1,1,1,0,0,20261012,20261023\n",
            )
        members = {k: cfg.GTFS_MEMBERS[k] for k in ("transit_trips", "transit_calendar")}
        out = _parse_gtfs(buf.getvalue(), members)
        trips = out["transit_trips"]
        assert len(trips) == 2
        assert list(trips.columns) == cfg.GTFS_MEMBERS["transit_trips"][1]
        assert trips["trip_id"].tolist() == ["0001", "0002"]  # zero-padding kept
        assert out["transit_calendar"]["start_date"].tolist() == ["20261012"]


# --------------------------------------------------------------------------- #
# dbt models, run against fixture raw tables                                  #
# --------------------------------------------------------------------------- #
def _render(model: str) -> str:
    """Model SQL with dbt Jinja replaced by plain DuckDB relation names."""
    path = next(MODELS.rglob(f"{model}.sql"))
    sql = path.read_text()
    sql = re.sub(r"\{\{\s*config\(.*?\)\s*\}\}", "", sql, flags=re.DOTALL)
    sql = re.sub(r"\{\{\s*source\('raw',\s*'(\w+)'\)\s*\}\}", r"raw.\1", sql)
    sql = re.sub(r"\{\{\s*ref\('(\w+)'\)\s*\}\}", r"\1", sql)
    assert "{{" not in sql, f"unrendered Jinja left in {model}"
    return sql


_DAYS = "monday,tuesday,wednesday,thursday,friday,saturday,sunday"


def _calendar(rows: list[tuple[str, str, str, str]]) -> pd.DataFrame:
    """(service_id, 7-char day mask Mon..Sun, start, end) -> calendar.txt frame."""
    out = []
    for sid, mask, start, end in rows:
        row = {"service_id": sid, "start_date": start, "end_date": end}
        row.update({d: mask[i] for i, d in enumerate(_DAYS.split(","))})
        out.append(row)
    return pd.DataFrame(out)


def _trips(spec: dict[tuple[str, str], int]) -> pd.DataFrame:
    rows = []
    for (route, service), n in spec.items():
        for i in range(n):
            rows.append(
                {
                    "route_id": route,
                    "service_id": service,
                    "trip_id": f"{route}-{service}-{i}",
                    "direction_id": str(i % 2),
                }
            )
    return pd.DataFrame(rows)


ROUTES = pd.DataFrame(
    {
        "route_id": ["R1", "R2", "R3"],
        "route_short_name": ["72", "MAX Blue", "99"],
        "route_long_name": ["Killingsworth/82nd", "MAX Blue Line", "Ghost route"],
        "route_type": ["3", "0", "3"],
        "route_color": [None, "084C8D", None],
    }
)

CALENDAR = _calendar(
    [
        ("W1", "1111100", "20261012", "20261023"),  # current weekday period
        ("W2", "1111100", "20261026", "20261127"),  # next weekday period (not yet)
        ("SA", "0000010", "20261017", "20261024"),
        ("SU", "0000001", "20261025", "20261122"),
        ("SU_OLD", "0000001", "20261011", "20261018"),  # already ended
    ]
)

TRIPS = _trips(
    {
        ("R1", "W1"): 3,
        ("R1", "W2"): 5,
        ("R1", "SA"): 2,
        ("R1", "SU"): 1,
        ("R1", "SU_OLD"): 4,
        ("R2", "W1"): 2,
        ("R2", "SU"): 1,
    }
)


def _frequency(built_at: str) -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("create schema raw")
    raw = {
        "transit_routes": ROUTES,
        "transit_trips": TRIPS,
        "transit_calendar": CALENDAR,
        "build_metadata": pd.DataFrame(
            {"table_name": ["transit_trips"], "row_count": [len(TRIPS)], "built_at": [built_at]}
        ),
    }
    for name, frame in raw.items():
        con.register("_frame", frame)
        con.execute(f"create table raw.{name} as select * from _frame")
        con.unregister("_frame")
    for model in (
        "stg_transit_routes",
        "stg_transit_trips",
        "stg_transit_calendar",
        "stg_build_metadata",
    ):
        con.execute(f"create view {model} as {_render(model)}")
    return con.execute(_render("mart_transit_route_frequency")).df().set_index("route_id")


@pytest.fixture(scope="module")
def freq() -> pd.DataFrame:
    return _frequency(BUILT_AT)


class TestRouteFrequencyMart:
    def test_one_row_per_route_including_routes_with_no_trips(self, freq):
        assert sorted(freq.index) == ["R1", "R2", "R3"]
        assert freq.loc["R3", ["weekday_trips", "saturday_trips", "sunday_trips"]].tolist() == [0, 0, 0]

    def test_counts_only_services_active_on_the_reference_day(self, freq):
        # R1 weekday: W1 (3) is active on Wed 10-21; W2 (5) has not started -> 3, not 8.
        assert freq.loc["R1", "weekday_trips"] == 3
        assert freq.loc["R1", "saturday_trips"] == 2
        # Sunday 10-25: SU (1) is active, SU_OLD (4) ended 10-18 -> 1, not 5.
        assert freq.loc["R1", "sunday_trips"] == 1

    def test_route_without_saturday_service_reports_zero(self, freq):
        assert freq.loc["R2", ["weekday_trips", "saturday_trips", "sunday_trips"]].tolist() == [2, 0, 1]

    def test_reference_dates_follow_the_build_date(self, freq):
        r = freq.loc["R1"]
        assert str(pd.Timestamp(r["weekday_date"]).date()) == "2026-10-21"
        assert str(pd.Timestamp(r["saturday_date"]).date()) == "2026-10-24"
        assert str(pd.Timestamp(r["sunday_date"]).date()) == "2026-10-25"

    def test_route_attributes_carried_from_routes(self, freq):
        assert freq.loc["R2", "mode"] == "MAX Light Rail"
        assert freq.loc["R1", "route_short_name"] == "72"

    def test_stale_build_clamps_the_reference_week_into_the_feed(self):
        # Built long after the feed's last service date: the reference week is
        # clamped to the feed's final week rather than finding no service at all.
        late = _frequency("2027-06-01T00:00:00+00:00")
        assert late["weekday_trips"].sum() > 0
        assert late.loc["R1", "weekday_trips"] == 5  # W2 is the period in effect then
