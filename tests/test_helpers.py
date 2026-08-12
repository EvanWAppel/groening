"""TDD for the pure warehouse-build helpers ported from Elvis."""

import math

import pandas as pd

from build_warehouse import _centroid, _epoch_to_date

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
