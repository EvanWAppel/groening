"""Multnomah County marriages — aggregate yearly counts (Oregon OHA)."""

import altair as alt
import streamlit as st

from app_db import query

st.title("💍 Marriages")
st.caption(
    "Marriages recorded in Multnomah County per year (Oregon Health Authority "
    "vital statistics). Oregon doesn't publish per-couple records like Clark "
    "County, NV — these are aggregate counts, with a same-sex breakout."
)

# --- KPIs ---
latest = query(
    "select year, total, same_sex, same_sex_pct from main.mart_marriage_annual "
    "where not preliminary order by year desc limit 1"
)
peak = query("select year, total from main.mart_marriage_annual order by total desc limit 1")
c1, c2, c3 = st.columns(3)
c1.metric(f"Marriages ({int(latest['year'][0])})", f"{int(latest['total'][0]):,}")
c2.metric("Same-sex share", f"{latest['same_sex_pct'][0]:.0f}%")
c3.metric("Peak year", f"{int(peak['total'][0]):,} ({int(peak['year'][0])})")

st.divider()

# --- Annual total ---
st.subheader("Marriages per year")
annual = query(
    "select year, total, same_sex, same_sex_pct, preliminary from main.mart_marriage_annual order by year"
)
total_chart = (
    alt.Chart(annual)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#c1121f")
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("total:Q", title="Marriages"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("total:Q", title="Marriages", format=","),
            alt.Tooltip("same_sex:Q", title="Same-sex", format=","),
        ],
    )
)
st.altair_chart(total_chart, width="stretch")

# --- Same-sex share over time ---
st.subheader("Same-sex marriages as a share of the total")
st.caption("Oregon legalized same-sex marriage in May 2014 — note the spike that year.")
share = (
    alt.Chart(annual)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_line(color="#3f88c5", point=True)
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("same_sex_pct:Q", title="Same-sex share (%)"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("same_sex_pct:Q", title="Same-sex %", format=".1f"),
        ],
    )
)
st.altair_chart(share, width="stretch")
st.caption("The two most recent years are preliminary (OHA).")
