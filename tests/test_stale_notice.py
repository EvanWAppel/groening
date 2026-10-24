"""TDD for the page notice shown when a topic was served from its last good
snapshot because the live source failed (DECISIONS.md 2026-10-24)."""

import pandas as pd

import city_config as cfg
import ui


def _stale(**dates) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "table_name": list(dates),
            "snapshot_as_of": pd.to_datetime(list(dates.values())),
        }
    )


class TestTopicTables:
    def test_most_pages_read_the_table_of_the_same_name(self):
        assert ui.topic_tables("crime") == ("crime",)

    def test_bike_page_reads_bike_network(self):
        assert ui.topic_tables("bike") == ("bike_network",)

    def test_transit_page_reads_every_gtfs_table(self):
        assert set(ui.topic_tables("transit")) == set(cfg.GTFS_MEMBERS)

    def test_every_fallback_table_is_reachable_from_some_page(self):
        reachable = {t for topic in ui.TOPICS for t in ui.topic_tables(topic)}
        assert cfg.SNAPSHOT_FALLBACK_TOPICS <= reachable


class TestStaleMessage:
    def test_live_topic_has_no_notice(self):
        assert ui.stale_message("crime", _stale(ugb="2026-10-01T08:00:00")) is None

    def test_no_stale_tables_means_no_notice(self):
        empty = pd.DataFrame({"table_name": [], "snapshot_as_of": pd.to_datetime([])})
        assert ui.stale_message("crime", empty) is None

    def test_stale_topic_names_the_snapshot_date(self):
        msg = ui.stale_message("ugb", _stale(ugb="2026-10-01T08:00:00"))
        assert msg is not None
        assert "October 1, 2026" in msg
        assert "snapshot" in msg.lower()

    def test_multi_table_topic_uses_the_oldest_snapshot(self):
        msg = ui.stale_message(
            "transit",
            _stale(transit_routes="2026-10-03T00:00:00", transit_trips="2026-09-30T00:00:00"),
        )
        assert msg is not None
        assert "September 30, 2026" in msg

    def test_unknown_snapshot_date_still_warns(self):
        rows = pd.DataFrame({"table_name": ["ugb"], "snapshot_as_of": pd.to_datetime([None])})
        msg = ui.stale_message("ugb", rows)
        assert msg is not None
        assert "unknown" in msg.lower()
