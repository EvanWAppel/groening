"""TDD for unifying the PortlandMaps service-request layers (E7b)."""

import duckdb
import pandas as pd
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

    def test_float_ids_from_a_nan_column_render_without_decimal(
        self, graffiti_frame, potholes_frame
    ):
        # pandas upcasts an int id column to float once any value is NaN; the id
        # must still read "5001", not "5001.0".
        potholes_frame["ITEM_ID"] = potholes_frame["ITEM_ID"].astype(float)
        out = unify_service_requests(graffiti_frame, potholes_frame)
        assert out["request_id"].tolist()[-2:] == ["5001", "5002"]

    def test_null_id_raises_rather_than_shipping_nan(self, graffiti_frame, potholes_frame):
        graffiti_frame["Id"] = graffiti_frame["Id"].astype(object)
        graffiti_frame.loc[1, "Id"] = None
        with pytest.raises(ValueError, match="Graffiti.*null"):
            unify_service_requests(graffiti_frame, potholes_frame)

    def test_undated_rows_are_logged(self, graffiti_frame, potholes_frame, caplog):
        with caplog.at_level("WARNING", logger="build_warehouse"):
            unify_service_requests(graffiti_frame, potholes_frame)
        assert any("Graffiti" in r.message and "1 of 3" in r.message for r in caplog.records)


class TestStgServiceRequests:
    """stg_service_requests SQL run for real over a tiny raw.service_requests."""

    @staticmethod
    def _run(render_model, rows: list[dict], session_tz: str = "UTC") -> pd.DataFrame:
        raw = pd.DataFrame(
            [
                {
                    "request_type": "Graffiti",
                    "request_id": str(i),
                    "status": "Closed",
                    "raw_status": "closed",
                    "created_at": "2024-01-05 10:00:00",
                    "hood_name": "Buckman",
                    "longitude": -122.65,
                    "latitude": 45.51,
                }
                | row
                for i, row in enumerate(rows)
            ]
        )
        con = duckdb.connect()
        try:
            # The build container (Railway) runs in UTC; pin it so the test does too.
            con.execute(f"set TimeZone = '{session_tz}'")
            con.execute("create schema raw")
            con.register("raw_df", raw)
            # An all-null pandas column has no type; the raw table holds text.
            con.execute(
                "create table raw.service_requests as "
                "select * replace (resolution::varchar as resolution) from raw_df"
            )
            return con.execute(render_model("stg_service_requests")).df()
        finally:
            con.close()

    def test_known_graffiti_outcomes_are_bucketed(self, render_model):
        out = self._run(
            render_model,
            [
                {"resolution": "Solved - Cleaned by contractor"},
                {"resolution": None},
                {"resolution": "Pending"},
                {"request_type": "Pothole", "resolution": None},
            ],
        )
        assert out["resolution"].tolist()[:3] == [
            "Cleaned by contractor",
            "Not recorded",
            "Open / pending",
        ]
        assert pd.isna(out["resolution"].iloc[3])

    def test_unmapped_graffiti_status_raises(self, render_model):
        with pytest.raises(duckdb.Error, match="Unmapped graffiti status: Painted over by elves"):
            self._run(render_model, [{"resolution": "Painted over by elves"}])

    @pytest.mark.parametrize("session_tz", ["UTC", "America/Los_Angeles", "Asia/Tokyo"])
    def test_future_cutoff_is_portland_wall_time(self, render_model, session_tz):
        # created_at is Portland local time (fetch_layer converts), so a report
        # from a few minutes ago must survive the "not in the future" filter
        # wherever the build runs.
        now_local = pd.Timestamp.now(tz="America/Los_Angeles").tz_localize(None)
        recent = (now_local - pd.Timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        future = (now_local + pd.Timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        out = self._run(
            render_model,
            [
                {"resolution": None, "created_at": recent},
                {"resolution": None, "created_at": future},
            ],
            session_tz,
        )
        assert out["request_id"].tolist() == ["0"]
