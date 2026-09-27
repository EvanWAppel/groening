"""TDD for the pure point-in-polygon neighborhood tagging helpers.

These power the choropleth maps: at build time every geocoded point (crime,
trees, permits, historic) is tagged with the Portland neighborhood whose polygon
contains it, so dbt can produce per-neighborhood counts with a plain GROUP BY —
no DuckDB spatial extension, no runtime geo dependency.
"""

import json

import pandas as pd

from build_warehouse import (
    _neighborhood_polygons,
    _point_in_ring,
    _ring_bbox,
    assign_neighborhood,
    tag_neighborhoods,
)

# Two edge-sharing squares: West = (0,0)-(2,2), East = (2,0)-(4,2). Rings are
# closed (first vertex repeated at the end), as ArcGIS returns them.
WEST = [[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]
EAST = [[2, 0], [2, 2], [4, 2], [4, 0], [2, 0]]


def _hoods_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"name": "West", "boundary_json": json.dumps(WEST)},
            {"name": "East", "boundary_json": json.dumps(EAST)},
        ]
    )


class TestPointInRing:
    def test_interior_point_is_inside(self):
        assert _point_in_ring(1.0, 1.0, WEST) is True

    def test_exterior_point_is_outside(self):
        assert _point_in_ring(3.0, 1.0, WEST) is False

    def test_far_point_is_outside(self):
        assert _point_in_ring(-5.0, -5.0, WEST) is False


class TestRingBbox:
    def test_bbox_is_min_max_of_ring(self):
        assert _ring_bbox(WEST) == (0, 0, 2, 2)


class TestNeighborhoodPolygons:
    def test_parses_name_ring_and_bbox(self):
        polys = _neighborhood_polygons(_hoods_df())
        assert [p["name"] for p in polys] == ["West", "East"]
        assert polys[0]["ring"] == WEST
        assert polys[0]["bbox"] == (0, 0, 2, 2)

    def test_skips_empty_geometry(self):
        df = pd.DataFrame([{"name": "Empty", "boundary_json": json.dumps([])}])
        assert _neighborhood_polygons(df) == []


class TestAssignNeighborhood:
    def test_point_in_west(self):
        polys = _neighborhood_polygons(_hoods_df())
        assert assign_neighborhood(1.0, 1.0, polys) == "West"

    def test_point_in_east(self):
        polys = _neighborhood_polygons(_hoods_df())
        assert assign_neighborhood(3.0, 1.0, polys) == "East"

    def test_point_outside_all_is_none(self):
        polys = _neighborhood_polygons(_hoods_df())
        assert assign_neighborhood(9.0, 9.0, polys) is None

    def test_none_coordinates_are_none(self):
        polys = _neighborhood_polygons(_hoods_df())
        assert assign_neighborhood(None, None, polys) is None

    def test_nan_coordinates_are_none(self):
        polys = _neighborhood_polygons(_hoods_df())
        assert assign_neighborhood(float("nan"), float("nan"), polys) is None

    def test_string_coordinates_are_coerced(self):
        # Raw ArcGIS lon/lat often arrive as strings; they must still resolve.
        polys = _neighborhood_polygons(_hoods_df())
        assert assign_neighborhood("1.0", "1.0", polys) == "West"

    def test_empty_string_coordinates_are_none(self):
        polys = _neighborhood_polygons(_hoods_df())
        assert assign_neighborhood("", "", polys) is None


class TestTagNeighborhoods:
    def test_adds_hood_name_column_preserving_rows(self):
        polys = _neighborhood_polygons(_hoods_df())
        df = pd.DataFrame(
            {
                "longitude": [1.0, 3.0, 9.0],
                "latitude": [1.0, 1.0, 9.0],
                "other": ["a", "b", "c"],
            }
        )
        out = tag_neighborhoods(df, polys)
        assert list(out["hood_name"]) == ["West", "East", None]
        assert list(out["other"]) == ["a", "b", "c"]  # untouched
        assert len(out) == 3

    def test_does_not_mutate_input(self):
        polys = _neighborhood_polygons(_hoods_df())
        df = pd.DataFrame({"longitude": [1.0], "latitude": [1.0]})
        tag_neighborhoods(df, polys)
        assert "hood_name" not in df.columns
