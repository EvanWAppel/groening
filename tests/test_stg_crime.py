"""stg_crime's future-dated filter reads REPORTED_DATETIME as Portland wall time."""

import duckdb
import pandas as pd
import pytest


@pytest.mark.parametrize("session_tz", ["UTC", "America/Los_Angeles", "Asia/Tokyo"])
def test_future_cutoff_is_portland_wall_time(render_model, session_tz):
    # fetch_layer emits Portland local time, so a report from a few minutes ago
    # survives and one two hours ahead is dropped, wherever the build runs.
    now_local = pd.Timestamp.now(tz="America/Los_Angeles").tz_localize(None)
    stamps = [now_local - pd.Timedelta(minutes=5), now_local + pd.Timedelta(hours=2)]
    raw = pd.DataFrame(
        {
            "REPORTED_DATETIME": [t.strftime("%Y-%m-%d %H:%M:%S") for t in stamps],
            "CategoryName": ["Property", "Property"],
            "OffenseGroupDescription": ["Larceny", "Larceny"],
            "CrimeType": ["Theft", "Theft"],
            "hood_name": ["Buckman", "Buckman"],
            "longitude": [-122.65, -122.65],
            "latitude": [45.51, 45.51],
        }
    )
    con = duckdb.connect()
    try:
        con.execute(f"set TimeZone = '{session_tz}'")
        con.execute("create schema raw")
        con.register("raw_df", raw)
        con.execute("create table raw.crime as select * from raw_df")
        out = con.execute(render_model("stg_crime")).df()
    finally:
        con.close()
    assert len(out) == 1
    assert out["reported_at"].iloc[0] == stamps[0].floor("s")
