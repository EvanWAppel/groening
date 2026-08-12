"""TDD for the pure warehouse-build helpers ported from Elvis."""

import math

import pandas as pd
import pytest

from build_warehouse import (
    _centroid,
    _epoch_to_date,
    _parse_usgs_dv,
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
