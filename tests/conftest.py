"""Shared pytest fixtures (DRY) for the Groening warehouse-build helpers."""

import pytest


@pytest.fixture
def point_geom() -> dict:
    """An ArcGIS point geometry (already reprojected to WGS84)."""
    return {"x": -122.664, "y": 45.589}


@pytest.fixture
def polygon_geom() -> dict:
    """An ArcGIS polygon geometry with a closed outer ring (first == last).

    The unit square (0,0)-(2,0)-(2,2)-(0,2) has centroid (1, 1).
    """
    return {"rings": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}
