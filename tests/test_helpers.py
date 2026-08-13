"""TDD for the pure warehouse-build helpers ported from Elvis."""

import datetime
import itertools
import math

import pandas as pd
import pytest

from build_warehouse import (
    _centroid,
    _collect_window,
    _epoch_to_date,
    _inspection_windows,
    _months_ago,
    _paginate,
    _parse_usgs_dv,
    _search_body,
    _split_window,
    _webmerc_to_wgs84,
)

# ArcGIS epoch-millisecond timestamp for 1996-01-30 (matches a real permit row).
ISSUE_MS_1996 = 822960000000


class TestCentroid:
    def test_none_geometry_returns_none_pair(self):
        assert _centroid(None) == (None, None)

    def test_empty_dict_returns_none_pair(self):
        assert _centroid({}) == (None, None)

    def test_point_returns_x_y(self, point_geom):
        assert _centroid(point_geom) == (-122.664, 45.589)

    def test_polygon_returns_ring_vertex_average(self, polygon_geom):
        lon, lat = _centroid(polygon_geom)
        # Closing duplicate vertex is dropped, so the average is over 4 corners.
        assert lon is not None and lat is not None
        assert math.isclose(lon, 1.0)
        assert math.isclose(lat, 1.0)


class TestEpochToDate:
    def test_none_returns_none(self):
        assert _epoch_to_date(None) is None

    def test_nan_returns_none(self):
        assert _epoch_to_date(float("nan")) is None

    def test_pre_1990_sentinel_returns_none(self):
        # Epoch 0 = 1970-01-01, below the 1990 "no date" cutoff.
        assert _epoch_to_date(0) is None

    def test_valid_epoch_ms_returns_iso_date(self):
        result = _epoch_to_date(ISSUE_MS_1996)
        assert result == "1996-01-30"
        # Round-trips through pandas cleanly.
        assert pd.to_datetime(result).year == 1996


class TestWebMercToWgs84:
    def test_origin_maps_to_null_island(self):
        lon, lat = _webmerc_to_wgs84(0.0, 0.0)
        assert math.isclose(lon, 0.0, abs_tol=1e-9)
        assert math.isclose(lat, 0.0, abs_tol=1e-9)

    def test_portland_str_sample_reprojects_to_central_portland(self):
        # Verbatim web_merc_x/y from a real ASTR report record.
        lon, lat = _webmerc_to_wgs84(-13653311.461585829, 5706443.927988703)
        assert math.isclose(lon, -122.64978, abs_tol=1e-4)
        assert math.isclose(lat, 45.53689, abs_tol=1e-4)


class TestParseUsgsDv:
    def test_extracts_points_and_drops_sentinel(self, usgs_dv_payload):
        df = _parse_usgs_dv(usgs_dv_payload)
        # The -999999 gap row is dropped, leaving 2 real points.
        assert list(df["date"]) == ["1972-10-01", "2026-07-01"]
        assert list(df["discharge_cfs"]) == [16400.0, 7790.0]
        assert list(df["provisional"]) == [False, True]

    def test_raises_when_no_timeseries(self):
        with pytest.raises(ValueError, match="no timeSeries"):
            _parse_usgs_dv({"value": {"timeSeries": []}})


# --------------------------------------------------------------------------- #
# Restaurant inspections (MyHealthDepartment searchInspections API)            #
#                                                                              #
# The API date-filters, caps a single query at ~225 rows, and pages 25 at a   #
# time — so the fetcher tiles a rolling window into date ranges and splits any #
# range that overflows the cap. These helpers are the pure/testable core.     #
# --------------------------------------------------------------------------- #
def _fake_rows(n: int, prefix: str) -> list[dict]:
    return [{"inspectionID": f"{prefix}-{i}"} for i in range(n)]


class TestMonthsAgo:
    def test_subtracts_months(self):
        assert _months_ago(datetime.date(2026, 8, 12), 6) == datetime.date(2026, 2, 12)

    def test_wraps_year(self):
        assert _months_ago(datetime.date(2026, 2, 12), 6) == datetime.date(2025, 8, 12)

    def test_clamps_day_to_shorter_month(self):
        # Aug 31 - 6 months -> Feb 28 (2026 is not a leap year).
        assert _months_ago(datetime.date(2026, 8, 31), 6) == datetime.date(2026, 2, 28)


class TestInspectionWindows:
    def test_covers_rolling_window_edges(self):
        wins = _inspection_windows(datetime.date(2026, 8, 12), 6, 7)
        assert wins[0][0] == "2026-02-12"
        assert wins[-1][1] == "2026-08-12"

    def test_windows_are_contiguous_and_bounded(self):
        wins = _inspection_windows(datetime.date(2026, 8, 12), 6, 7)
        for start, end in wins:
            span = datetime.date.fromisoformat(end) - datetime.date.fromisoformat(start)
            assert 1 <= span.days + 1 <= 7
        for prev, nxt in itertools.pairwise(wins):
            prev_end = datetime.date.fromisoformat(prev[1])
            next_start = datetime.date.fromisoformat(nxt[0])
            assert next_start == prev_end + datetime.timedelta(days=1)


class TestSplitWindow:
    def test_halves_contiguously(self):
        left, right = _split_window("2026-02-12", "2026-02-18")
        assert left[0] == "2026-02-12"
        assert right[1] == "2026-02-18"
        left_end = datetime.date.fromisoformat(left[1])
        right_start = datetime.date.fromisoformat(right[0])
        assert right_start == left_end + datetime.timedelta(days=1)

    def test_two_day_window_splits_into_single_days(self):
        assert _split_window("2026-02-12", "2026-02-13") == (
            ("2026-02-12", "2026-02-12"),
            ("2026-02-13", "2026-02-13"),
        )


class TestSearchBody:
    def test_builds_search_inspections_payload(self):
        body = _search_body("multco-eh", "2026-02-12 to 2026-02-18", 50, 25)
        assert body["task"] == "searchInspections"
        assert body["data"]["path"] == "multco-eh"
        assert body["data"]["filters"]["date"] == "2026-02-12 to 2026-02-18"
        assert body["data"]["start"] == 50
        assert body["data"]["count"] == 25
        assert body["data"]["searchStr"] == ""


class TestPaginate:
    def test_stops_on_short_final_page(self):
        pages = [_fake_rows(25, "a"), _fake_rows(10, "b")]
        seen_starts = []

        def post(body):
            i = body["data"]["start"] // 25
            seen_starts.append(body["data"]["start"])
            return pages[i]

        rows, truncated = _paginate(post, "p", "d")
        assert len(rows) == 35
        assert truncated is False
        assert seen_starts == [0, 25]

    def test_empty_first_page_is_not_truncated(self):
        rows, truncated = _paginate(lambda body: [], "p", "d")
        assert rows == []
        assert truncated is False

    def test_error_object_terminates_cleanly(self):
        rows, truncated = _paginate(lambda body: {"err": True, "msg": "bad request"}, "p", "d")
        assert rows == []
        assert truncated is False

    def test_dedupes_by_inspection_id(self):
        page = _fake_rows(25, "dup")  # identical ids every page

        rows, truncated = _paginate(lambda body: page, "p", "d")
        assert len(rows) == 25  # 25 unique despite many full pages
        assert truncated is True  # full pages all the way to the cap

    def test_flags_truncation_at_cap(self):
        # Every page is full and unique -> the window exceeds the server cap.
        def post(body):
            return _fake_rows(25, f"s{body['data']['start']}")

        rows, truncated = _paginate(post, "p", "d")
        assert truncated is True
        assert len(rows) == 25 * 9  # offsets 0..200 => 9 pages before the 225 cap


class TestCollectWindow:
    def test_returns_rows_without_splitting_when_small(self):
        def post(body):
            return _fake_rows(10, "ok") if body["data"]["start"] == 0 else []

        rows = _collect_window(post, "p", "2026-02-12", "2026-02-18")
        assert len(rows) == 10

    def test_splits_busy_window_down_to_single_days(self):
        # Multi-day ranges overflow (always-full pages); single days return 5 rows.
        def post(body):
            start, end = body["data"]["filters"]["date"].split(" to ")
            offset = body["data"]["start"]
            if start == end:
                return _fake_rows(5, start) if offset == 0 else []
            return _fake_rows(25, f"{start}-{offset}")  # busy -> truncated

        rows = _collect_window(post, "p", "2026-02-12", "2026-02-14")
        ids = {r["inspectionID"] for r in rows}
        assert len(ids) == 15  # 3 single days x 5 rows each

    def test_single_day_overflow_is_accepted_not_infinite(self):
        def post(body):
            return _fake_rows(25, f"s{body['data']['start']}")  # always full

        rows = _collect_window(post, "p", "2026-02-12", "2026-02-12")
        assert len(rows) == 225  # capped and accepted; recursion terminates
