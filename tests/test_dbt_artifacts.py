"""TDD for parsing dbt target artifacts (run_results.json, manifest.json)."""

from dbt_artifacts import (
    build_lineage_dot,
    classify_test,
    lineage_edges,
    node_layer,
    summarize_dbt_tests,
)


def _result(unique_id: str, status: str) -> dict:
    return {"unique_id": unique_id, "status": status}


class TestClassifyTest:
    def test_not_null(self):
        assert classify_test("test.groening.not_null_mart_permits_monthly_issue_month.abc") == "not_null"

    def test_unique(self):
        assert classify_test("test.groening.unique_mart_build_metadata_table_name.abc") == "unique"

    def test_accepted_values(self):
        uid = "test.groening.accepted_values_mart_air_quality_bad_days_pollutant__Ozone__PM2_5.abc"
        assert classify_test(uid) == "accepted_values"

    def test_unrecognized_is_other(self):
        assert classify_test("test.groening.some_custom_singular_test.abc") == "other"


class TestSummarizeDbtTests:
    def test_counts_only_test_nodes_not_models(self):
        rr = {
            "results": [
                _result("model.groening.mart_permits_monthly", "success"),
                _result("test.groening.not_null_mart_permits_monthly_issue_month.a", "pass"),
                _result("test.groening.unique_mart_permits_monthly_issue_month.b", "pass"),
            ]
        }
        summary = summarize_dbt_tests(rr)
        assert summary["total"] == 2  # the model row is excluded
        assert summary["passed"] == 2
        assert summary["failed"] == 0

    def test_counts_failures_and_errors(self):
        rr = {
            "results": [
                _result("test.groening.not_null_a.x", "pass"),
                _result("test.groening.unique_b.y", "fail"),
                _result("test.groening.accepted_values_c.z", "error"),
            ]
        }
        summary = summarize_dbt_tests(rr)
        assert summary["total"] == 3
        assert summary["passed"] == 1
        assert summary["failed"] == 2

    def test_breakdown_by_type(self):
        rr = {
            "results": [
                _result("test.groening.not_null_a.x", "pass"),
                _result("test.groening.not_null_b.y", "pass"),
                _result("test.groening.unique_c.z", "fail"),
            ]
        }
        by_type = summarize_dbt_tests(rr)["by_type"]
        assert by_type["not_null"] == {"passed": 2, "total": 2}
        assert by_type["unique"] == {"passed": 0, "total": 1}  # one unique test, it failed

    def test_empty_results_is_zeroed(self):
        summary = summarize_dbt_tests({"results": []})
        assert summary == {"total": 0, "passed": 0, "failed": 0, "by_type": {}}


# A minimal manifest: raw.parks -> stg_parks -> mart_parks -> parks_page, plus a
# test node that must be excluded from lineage.
MANIFEST = {
    "sources": {
        "source.groening.raw.parks": {"schema": "raw", "name": "parks"},
    },
    "nodes": {
        "model.groening.stg_parks": {
            "resource_type": "model", "name": "stg_parks",
            "depends_on": {"nodes": ["source.groening.raw.parks"]},
        },
        "model.groening.mart_parks": {
            "resource_type": "model", "name": "mart_parks",
            "depends_on": {"nodes": ["model.groening.stg_parks"]},
        },
        "test.groening.not_null_mart_parks_id.abc": {
            "resource_type": "test", "name": "not_null_mart_parks_id",
            "depends_on": {"nodes": ["model.groening.mart_parks"]},
        },
    },
    "exposures": {
        "exposure.groening.parks_page": {
            "resource_type": "exposure", "name": "parks_page",
            "depends_on": {"nodes": ["model.groening.mart_parks"]},
        },
    },
}


class TestNodeLayer:
    def test_layers(self):
        assert node_layer("raw.parks") == "source"
        assert node_layer("stg_parks") == "staging"
        assert node_layer("mart_parks") == "mart"
        assert node_layer("parks_page") == "page"


class TestLineageEdges:
    def test_full_chain_edges(self):
        edges = set(lineage_edges(MANIFEST))
        assert ("raw.parks", "stg_parks") in edges
        assert ("stg_parks", "mart_parks") in edges
        assert ("mart_parks", "parks_page") in edges

    def test_test_nodes_are_excluded(self):
        edges = lineage_edges(MANIFEST)
        assert all("not_null" not in a and "not_null" not in b for a, b in edges)


class TestBuildLineageDot:
    def test_is_a_digraph_with_edges(self):
        dot = build_lineage_dot(lineage_edges(MANIFEST))
        assert dot.strip().startswith("digraph")
        assert '"raw.parks" -> "stg_parks"' in dot
        assert '"mart_parks" -> "parks_page"' in dot
