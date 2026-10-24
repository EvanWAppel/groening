"""TDD for the dead-source fallback (option (c), DECISIONS.md 2026-10-24).

A listed topic whose live fetch fails or returns zero rows loads its last good
snapshot from data/ instead of failing the deploy, and says so loudly. With no
snapshot it still fails exactly as before.
"""

import datetime
import logging
import urllib.error

import duckdb
import pandas as pd
import pytest

import build_warehouse
import city_config as cfg
from build_warehouse import (
    collect_build_metadata,
    fetch_or_snapshot,
    fetch_set_or_snapshot,
    read_snapshot,
    snapshot_path,
    write_snapshot,
)

AT = datetime.datetime(2026, 10, 20, 9, 30, tzinfo=datetime.UTC)
TRANSIT = ("transit_routes", "transit_stops", "transit_trips", "transit_calendar")


def _frame(tag: str, n: int = 2) -> pd.DataFrame:
    return pd.DataFrame({"id": list(range(n)), "tag": [tag] * n})


def _dead(err: Exception):
    def fetch():
        raise err

    return fetch


class TestFallbackTopicList:
    """Evan's 2026-10-24 list: everything except neighborhoods."""

    def test_exact_topic_list(self):
        assert cfg.SNAPSHOT_FALLBACK_TOPICS == {
            "ugb", "building_permits", "parks", "housing", "historic", "trees",
            "heritage_trees", "bike_network", "crime", "service_requests",
            "short_term_rentals", "weather", "willamette", "air_quality",
            "marriage", "tourism", *TRANSIT,
        }

    def test_neighborhoods_stays_fatal(self):
        assert "neighborhoods" not in cfg.SNAPSHOT_FALLBACK_TOPICS

    def test_every_listed_topic_is_a_catalogued_source(self):
        assert cfg.SNAPSHOT_FALLBACK_TOPICS <= set(cfg.SOURCES)


class TestSnapshotStore:
    def test_path_follows_the_inspections_naming(self, snapshot_dir):
        assert snapshot_path("ugb") == snapshot_dir / "ugb_raw.parquet"

    def test_round_trip_keeps_rows_and_date(self, snapshot_dir):
        write_snapshot("parks", _frame("live", 3), AT)
        df, taken = read_snapshot("parks")
        assert df["tag"].tolist() == ["live"] * 3
        assert taken == AT.isoformat()

    def test_date_lives_inside_the_file(self, snapshot_dir):
        """A git checkout resets mtimes, so the date must be in the Parquet itself."""
        write_snapshot("parks", _frame("live"), AT)
        meta = dict(
            duckdb.connect()
            .execute(
                "select key::varchar, value::varchar from parquet_kv_metadata(?)",
                [str(snapshot_path("parks"))],
            )
            .fetchall()
        )
        assert meta["snapshot_at"] == AT.isoformat()

    def test_refuses_to_write_an_empty_snapshot(self, snapshot_dir):
        with pytest.raises(ValueError, match="empty"):
            write_snapshot("parks", _frame("x", 0), AT)


class TestFetchOrSnapshot:
    def test_live_success_is_returned_and_refreshes_the_snapshot(self, snapshot_dir):
        fallbacks: dict[str, str] = {}
        df = fetch_or_snapshot("parks", lambda: _frame("live"), fallbacks, now=AT)
        assert df["tag"].tolist() == ["live", "live"]
        assert fallbacks == {}
        snap, taken = read_snapshot("parks")
        assert snap["tag"].tolist() == ["live", "live"]
        assert taken == AT.isoformat()

    def test_failed_fetch_falls_back_to_the_snapshot(self, snapshot_dir):
        write_snapshot("ugb", _frame("old"), AT)
        fallbacks: dict[str, str] = {}
        df = fetch_or_snapshot("ugb", _dead(ValueError("ugb: no feature returned")), fallbacks)
        assert df["tag"].tolist() == ["old", "old"]
        assert fallbacks == {"ugb": AT.isoformat()}

    def test_zero_rows_falls_back_to_the_snapshot(self, snapshot_dir):
        write_snapshot("crime", _frame("old"), AT)
        fallbacks: dict[str, str] = {}
        df = fetch_or_snapshot("crime", lambda: _frame("live", 0), fallbacks)
        assert df["tag"].tolist() == ["old", "old"]
        assert fallbacks == {"crime": AT.isoformat()}

    def test_zero_rows_never_clobbers_the_snapshot(self, snapshot_dir):
        write_snapshot("crime", _frame("old"), AT)
        fetch_or_snapshot("crime", lambda: _frame("live", 0), {})
        snap, taken = read_snapshot("crime")
        assert snap["tag"].tolist() == ["old", "old"]
        assert taken == AT.isoformat()

    def test_fallback_logs_a_loud_warning(self, snapshot_dir, caplog):
        write_snapshot("ugb", _frame("old"), AT)
        with caplog.at_level(logging.WARNING, logger="build_warehouse"):
            fetch_or_snapshot("ugb", _dead(ValueError("ugb: no feature returned")), {})
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "a fallback must log a WARNING"
        text = " ".join(r.getMessage() for r in warnings)
        assert "SNAPSHOT FALLBACK" in text
        assert "ugb" in text
        assert "ugb: no feature returned" in text
        assert "2026-10-20" in text

    def test_failure_without_a_snapshot_still_fails(self, snapshot_dir):
        err = urllib.error.URLError("dns down")
        fallbacks: dict[str, str] = {}
        with pytest.raises(urllib.error.URLError, match="dns down"):
            fetch_or_snapshot("weather", _dead(err), fallbacks)
        assert fallbacks == {}

    def test_zero_rows_without_a_snapshot_still_fails_at_load(self, snapshot_dir):
        """Unchanged from today: the empty frame reaches load_raw, which raises."""
        df = fetch_or_snapshot("weather", lambda: _frame("live", 0), {})
        assert df.empty
        with pytest.raises(ValueError, match="zero rows"):
            build_warehouse.load_raw(duckdb.connect(), "weather", df)

    def test_unlisted_topic_is_refused(self, snapshot_dir):
        """neighborhoods (or any new topic) must not be wired to a fallback by accident."""
        with pytest.raises(ValueError, match="neighborhoods"):
            fetch_or_snapshot("neighborhoods", lambda: _frame("live"), {})


class TestFetchSetOrSnapshot:
    """TriMet GTFS is one download feeding four tables; they fall back together
    so routes/stops/trips/calendar always come from the same feed version."""

    def _write_all(self):
        for t in TRANSIT:
            write_snapshot(t, _frame(f"old-{t}"), AT)

    def test_live_success_refreshes_every_member(self, snapshot_dir):
        live = {t: _frame(f"live-{t}") for t in TRANSIT}
        fallbacks: dict[str, str] = {}
        out = fetch_set_or_snapshot(TRANSIT, lambda: live, fallbacks, now=AT)
        assert {t: out[t]["tag"].iloc[0] for t in TRANSIT} == {t: f"live-{t}" for t in TRANSIT}
        assert fallbacks == {}
        for t in TRANSIT:
            assert read_snapshot(t)[0]["tag"].iloc[0] == f"live-{t}"

    def test_failed_download_falls_back_for_every_member(self, snapshot_dir):
        self._write_all()
        fallbacks: dict[str, str] = {}
        out = fetch_set_or_snapshot(TRANSIT, _dead(urllib.error.URLError("503")), fallbacks)
        assert {t: out[t]["tag"].iloc[0] for t in TRANSIT} == {t: f"old-{t}" for t in TRANSIT}
        assert fallbacks == {t: AT.isoformat() for t in TRANSIT}

    def test_one_empty_member_falls_back_the_whole_set(self, snapshot_dir):
        self._write_all()
        live = {t: _frame(f"live-{t}") for t in TRANSIT}
        live["transit_trips"] = _frame("live", 0)
        fallbacks: dict[str, str] = {}
        out = fetch_set_or_snapshot(TRANSIT, lambda: live, fallbacks)
        assert out["transit_routes"]["tag"].iloc[0] == "old-transit_routes"
        assert set(fallbacks) == set(TRANSIT)
        # ...and the good live members did not overwrite their snapshots.
        assert read_snapshot("transit_routes")[0]["tag"].iloc[0] == "old-transit_routes"

    def test_a_missing_member_snapshot_fails_like_today(self, snapshot_dir):
        self._write_all()
        snapshot_path("transit_stops").unlink()
        with pytest.raises(urllib.error.URLError):
            fetch_set_or_snapshot(TRANSIT, _dead(urllib.error.URLError("503")), {})


class TestProvenance:
    BUILT = datetime.datetime(2026, 10, 24, 12, 0, tzinfo=datetime.UTC)

    def test_snapshot_date_is_recorded_per_table(self):
        df = collect_build_metadata(
            {"parks": 3, "ugb": 1}, self.BUILT, {"ugb": AT.isoformat()}
        )
        by_table = dict(zip(df["table_name"], df["snapshot_as_of"], strict=True))
        assert by_table["ugb"] == AT.isoformat()
        assert pd.isna(by_table["parks"])

    def test_live_build_has_an_all_null_snapshot_column(self):
        df = collect_build_metadata({"parks": 3}, self.BUILT)
        assert "snapshot_as_of" in df.columns
        assert df["snapshot_as_of"].isna().all()

    def test_null_column_lands_as_varchar_in_duckdb(self):
        con = duckdb.connect()
        build_warehouse.load_raw(con, "build_metadata", collect_build_metadata({"parks": 3}, self.BUILT))
        types = {r[0]: r[1] for r in con.execute("describe raw.build_metadata").fetchall()}
        assert types["snapshot_as_of"] == "VARCHAR"


class TestMainWiring:
    """Every listed topic goes through the fallback in main(); neighborhoods doesn't."""

    @pytest.fixture
    def offline_build(self, snapshot_dir, tmp_path, monkeypatch):
        hood = [[-123.0, 45.0], [-122.0, 45.0], [-122.0, 46.0], [-123.0, 46.0], [-123.0, 45.0]]
        import json

        monkeypatch.setattr(build_warehouse, "DB_PATH", tmp_path / "test.duckdb")
        monkeypatch.setattr(
            build_warehouse,
            "fetch_neighborhoods",
            lambda: pd.DataFrame([{"name": "Testville", "boundary_json": json.dumps(hood)}]),
        )
        monkeypatch.setattr(build_warehouse, "fetch_inspections", lambda: _frame("insp"))
        names = [
            "fetch_building_permits", "fetch_parks", "fetch_housing", "fetch_historic",
            "fetch_weather", "fetch_willamette", "fetch_str", "fetch_crime",
            "fetch_service_requests", "fetch_air_quality", "fetch_trees",
            "fetch_heritage_trees", "fetch_bike_network", "fetch_transit", "fetch_ugb",
            "fetch_marriage", "fetch_tourism",
        ]
        for name in names:
            monkeypatch.setattr(build_warehouse, name, _dead(urllib.error.URLError(f"{name} down")))
        return tmp_path / "test.duckdb"

    def test_every_dead_listed_source_falls_back_and_is_stamped(self, offline_build):
        for t in cfg.SNAPSHOT_FALLBACK_TOPICS:
            write_snapshot(t, _frame(f"old-{t}"), AT)
        build_warehouse.main()
        con = duckdb.connect(str(offline_build), read_only=True)
        meta = dict(
            con.execute("select table_name, snapshot_as_of from raw.build_metadata").fetchall()
        )
        stale = {t for t, d in meta.items() if d is not None}
        assert stale == set(cfg.SNAPSHOT_FALLBACK_TOPICS)
        assert meta["neighborhoods"] is None
        assert meta["restaurant_inspections"] is None
        assert con.execute("select tag from raw.ugb limit 1").fetchone() == ("old-ugb",)

    def test_a_dead_source_without_a_snapshot_still_fails_the_build(self, offline_build):
        for t in cfg.SNAPSHOT_FALLBACK_TOPICS - {"marriage"}:
            write_snapshot(t, _frame(f"old-{t}"), AT)
        with pytest.raises(urllib.error.URLError, match="fetch_marriage down"):
            build_warehouse.main()

    def test_dead_neighborhoods_fails_even_with_a_snapshot_file(self, offline_build, monkeypatch):
        # A stray snapshot file must not rescue an unlisted topic.
        build_warehouse._write_parquet_snapshot(snapshot_path("neighborhoods"), _frame("old"), AT)
        monkeypatch.setattr(
            build_warehouse, "fetch_neighborhoods", _dead(urllib.error.URLError("hoods down"))
        )
        with pytest.raises(urllib.error.URLError, match="hoods down"):
            build_warehouse.main()
