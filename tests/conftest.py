"""Shared pytest fixtures (DRY) for the Groening warehouse-build helpers."""

from unittest.mock import Mock

import pytest

import build_warehouse


@pytest.fixture
def network(monkeypatch):
    """Replace the download network and clock; no external requests or real waits."""
    opener = Mock()
    sleep = Mock()
    monkeypatch.setattr(build_warehouse.urllib.request, "urlopen", opener)
    monkeypatch.setattr(build_warehouse.time, "sleep", sleep)
    return opener, sleep


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


@pytest.fixture
def usgs_dv_payload() -> dict:
    """A minimal USGS NWIS daily-values JSON envelope with one gap sentinel."""
    return {
        "value": {
            "timeSeries": [
                {
                    "values": [
                        {
                            "value": [
                                {"dateTime": "1972-10-01T00:00:00.000", "value": "16400", "qualifiers": ["A"]},
                                {"dateTime": "2026-07-01T00:00:00.000", "value": "7790", "qualifiers": ["P"]},
                                {"dateTime": "2026-07-02T00:00:00.000", "value": "-999999", "qualifiers": ["P"]},
                            ]
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def graffiti_frame():
    """A tiny BPS Graffiti Reports frame, shaped as fetch_layer returns it."""
    import pandas as pd

    return pd.DataFrame(
        {
            "OBJECTID": [1, 2, 3],
            "Id": [101, 102, 103],
            "Status": ["closed", "Pending", "solved"],
            "CreatedAt": ["2024-01-05 10:00:00", "2024-02-10 09:30:00", None],
            "UpdatedAt": ["2024-01-09 12:00:00", "2024-02-11 08:00:00", "2024-03-01 00:00:00"],
            "Graffiti_Status": ["Solved - Cleaned by contractor", None, "SOLVED"],
            "Square_footage": ["20", None, "5"],
            "longitude": [-122.66, -122.60, -122.70],
            "latitude": [45.52, 45.50, 45.55],
        }
    )


@pytest.fixture
def potholes_frame():
    """A tiny PBOT Pothole Repair Reports frame, shaped as fetch_layer returns it."""
    import pandas as pd

    return pd.DataFrame(
        {
            "OBJECTID": [7, 8],
            "ITEM_ID": [5001, 5002],
            "ITEM_STATUS": ["Closed", "In Progress"],
            "ITEM_DATE_CREATED": ["2025-11-01 14:00:00", "2026-01-15 07:45:00"],
            "ITEM_CATEGORY_NAME": ["Pothole Hotline 823-BUMP (2867)"] * 2,
            "LOCATION_NEIGHBORHOOD": ["Buckman", "Lents"],
            "longitude": [-122.65, -122.57],
            "latitude": [45.51, 45.48],
        }
    )
