"""Sources & Methodology — where every number on this site comes from."""

import pandas as pd
import streamlit as st

import city_config as cfg
from app_db import query
from dbt_artifacts import (
    build_lineage_dot,
    lineage_edges,
    load_manifest,
    load_run_results,
    summarize_dbt_tests,
)
from ui import build_stamp

st.page_link("views/overview.py", label="← All datasets")
st.html('<div class="eyebrow detail-eyebrow">Colophon <span>／ Methodology</span></div>')
st.title("Sources & Methodology")
st.caption(
    "Groening is a parameterized ELT pipeline. `build_warehouse.py` fetches each "
    "public source into `raw.*` tables in a DuckDB file; dbt then models them into "
    "`staging` views (light normalization) and `marts` tables (viz-ready "
    "aggregations) that the pages read. The warehouse is rebuilt from scratch on "
    "every deploy — nothing is hand-edited — and dbt data-quality tests gate the "
    "build, so a duplicate key or out-of-domain value fails before the app can "
    "read it. Every source below is public and machine-readable."
)
st.html(f'<p class="footer-provenance">{build_stamp()}</p>')

# Row counts come from the build-provenance mart; provenance from the city config.
counts = dict(
    query("select table_name, row_count from main.mart_build_metadata").itertuples(
        index=False, name=None
    )
)
rows = cfg.source_catalog_rows(counts)

st.subheader("The datasets")
catalog = pd.DataFrame(rows)[
    ["title", "publisher", "coverage", "row_count", "grain", "license", "url"]
]
st.dataframe(
    catalog,
    hide_index=True,
    width="stretch",
    column_config={
        "title": st.column_config.TextColumn("Dataset"),
        "publisher": st.column_config.TextColumn("Publisher"),
        "coverage": st.column_config.TextColumn("Coverage"),
        "row_count": st.column_config.NumberColumn("Rows", format="%d"),
        "grain": st.column_config.TextColumn("Grain / transform", width="large"),
        "license": st.column_config.TextColumn("Terms"),
        "url": st.column_config.LinkColumn("Source", display_text="endpoint ↗"),
    },
)
st.caption(
    f"{len(catalog)} datasets · {int(catalog['row_count'].sum()):,} rows. "
    "“Source” links to the exact endpoint the pipeline fetches. Licensing for "
    "federal sources (EPA, NOAA, USGS, BTS) is U.S. public domain; municipal and "
    "state terms are summarized — consult each publisher for exact terms."
)

st.divider()

# --- Data quality (E4): dbt tests that gate every build ---------------------- #
st.subheader("Data quality")
run_results = load_run_results()
if run_results is None:
    st.info("Run `dbt build` to populate the data-quality summary.")
else:
    tests = summarize_dbt_tests(run_results)
    verdict = "all passing" if tests["failed"] == 0 else f"{tests['failed']} failing"
    st.markdown(
        f"**{tests['passed']} of {tests['total']} dbt data-quality tests {verdict}.** "
        "These run as part of `dbt build`, so a duplicate grain key, an unexpected "
        "null, or an out-of-domain category fails the build before the app can read "
        "bad data."
    )
    labels = {
        "not_null": "Not null", "unique": "Unique",
        "accepted_values": "Accepted values", "relationships": "Relationships",
        "accepted_range": "Accepted range", "other": "Other",
    }
    breakdown = tests["by_type"]
    cols = st.columns(len(breakdown))
    for col, (test_type, counts) in zip(cols, breakdown.items()):
        col.metric(labels.get(test_type, test_type), f"{counts['passed']}/{counts['total']}")

st.divider()

# --- Pipeline lineage (E3): source -> staging -> mart -> page ---------------- #
st.subheader("Pipeline lineage")
manifest = load_manifest()
if manifest is None:
    st.info("Run `dbt build` to render the lineage graph.")
else:
    st.caption(
        "Every edge below is read straight from dbt's `manifest.json`: each public "
        "source flows through a `staging` view into one or more `marts` tables, "
        "which a Streamlit page (a dbt *exposure*) then reads. Nothing here is drawn "
        "by hand — it is the actual build graph."
    )
    st.graphviz_chart(build_lineage_dot(lineage_edges(manifest)), width="stretch")

st.divider()

st.subheader("Dropped topics")
st.caption(
    "Topics from the original Las Vegas blueprint that Portland does not publish "
    "in a clean, machine-readable form. They are dropped and logged rather than "
    "faked, so a missing page never reads as “done.”"
)
for topic, reason in cfg.DROPPED_TOPICS.items():
    label = topic.replace("_", " ").title()
    st.markdown(f"- **{label}** — {reason}")
