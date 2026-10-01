"""TDD for unifying the PortlandMaps service-request layers (E7b)."""

import pytest

from build_warehouse import SERVICE_REQUEST_COLUMNS, unify_service_requests


class TestUnifyServiceRequests:
    def test_stacks_both_types_with_the_shared_column_set(self, graffiti_frame, potholes_frame):
        out = unify_service_requests(graffiti_frame, potholes_frame)
        assert list(out.columns) == SERVICE_REQUEST_COLUMNS
        assert len(out) == len(graffiti_frame) + len(potholes_frame)
        assert out["request_type"].value_counts().to_dict() == {"Graffiti": 3, "Pothole": 2}

    def test_status_normalized_to_open_or_closed(self, graffiti_frame, potholes_frame):
        out = unify_service_requests(graffiti_frame, potholes_frame)
        # closed / solved -> Closed; pending / in progress -> Open (case-insensitive).
        assert out["status"].tolist() == ["Closed", "Open", "Closed", "Closed", "Open"]

    def test_raw_status_and_ids_are_kept(self, graffiti_frame, potholes_frame):
        out = unify_service_requests(graffiti_frame, potholes_frame)
        assert out["request_id"].tolist() == ["101", "102", "103", "5001", "5002"]
        assert out["raw_status"].tolist() == ["closed", "Pending", "solved", "Closed", "In Progress"]

    def test_graffiti_resolution_detail_carried_potholes_none(self, graffiti_frame, potholes_frame):
        out = unify_service_requests(graffiti_frame, potholes_frame)
        detail = out.set_index("request_id")["resolution"]
        assert detail["101"] == "Solved - Cleaned by contractor"
        assert detail["102"] is None
        assert detail["5001"] is None

    def test_created_at_and_coordinates_mapped(self, graffiti_frame, potholes_frame):
        out = unify_service_requests(graffiti_frame, potholes_frame).set_index("request_id")
        assert out.loc["101", "created_at"] == "2024-01-05 10:00:00"
        assert out.loc["103", "created_at"] is None
        assert out.loc["5002", "created_at"] == "2026-01-15 07:45:00"
        assert out.loc["5001", "longitude"] == -122.65
        assert out.loc["5001", "latitude"] == 45.51

    def test_unknown_status_raises_rather_than_guessing(self, graffiti_frame, potholes_frame):
        potholes_frame.loc[0, "ITEM_STATUS"] = "Deferred"
        with pytest.raises(ValueError, match="Deferred"):
            unify_service_requests(graffiti_frame, potholes_frame)

    def test_empty_layer_raises(self, graffiti_frame, potholes_frame):
        with pytest.raises(ValueError, match="Pothole"):
            unify_service_requests(graffiti_frame, potholes_frame.iloc[0:0])
