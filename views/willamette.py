"""The Willamette River — Portland's signature water body (USGS daily discharge)."""

import altair as alt
import streamlit as st

from app_db import query

st.title("🌊 The Willamette River")
st.caption(
    "Daily mean streamflow of the Willamette River at Portland (USGS gauge "
    "14211720), 1972–present. Portland's answer to a reservoir-level page — the "
    "river's floods and summer lows in one long series."
)

# --- KPIs ---
latest = query(
    "select obs_date, discharge_cfs, provisional from main.mart_willamette_daily "
    "order by obs_date desc limit 1"
)
ext = query(
    "select max(discharge_cfs) as hi, min(discharge_cfs) as lo from main.mart_willamette_daily"
)
span = query("select min(obs_date) as first, max(obs_date) as last from main.mart_willamette_daily")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest flow", f"{latest['discharge_cfs'][0]:,.0f} cfs")
c2.metric("Record high (flood)", f"{ext['hi'][0]:,.0f} cfs")
c3.metric("Record low", f"{ext['lo'][0]:,.0f} cfs")
c4.metric("Record since", f"{span['first'][0]:%Y}")

st.divider()

# --- Monthly average discharge (smoothed long series) ---
st.subheader("Monthly average discharge")
monthly = query("select month, avg_cfs from main.mart_willamette_monthly order by month")
flow = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_area(color="#3f88c5", opacity=0.7)
    .encode(
        x=alt.X("month:T", title=None),
        y=alt.Y("avg_cfs:Q", title="Discharge (cfs)", axis=alt.Axis(format="~s")),
        tooltip=[
            alt.Tooltip("month:T", title="Month"),
            alt.Tooltip("avg_cfs:Q", title="Avg cfs", format=",.0f"),
        ],
    )
)
st.altair_chart(flow, width="stretch")

# --- Seasonal shape: average discharge by calendar month ---
st.subheader("Seasonal flow (average by calendar month)")
seasonal = query(
    """
    select monthname(obs_date) as month_name,
           extract('month' from obs_date) as month_num,
           avg(discharge_cfs) as avg_cfs
    from main.mart_willamette_daily
    group by 1, 2
    order by 2
    """
)
seasonal_chart = (
    alt.Chart(seasonal)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2e8b57")
    .encode(
        x=alt.X("month_name:N", sort=list(seasonal["month_name"]), title=None),
        y=alt.Y("avg_cfs:Q", title="Avg discharge (cfs)", axis=alt.Axis(format="~s")),
        tooltip=[
            alt.Tooltip("month_name:N", title="Month"),
            alt.Tooltip("avg_cfs:Q", title="Avg cfs", format=",.0f"),
        ],
    )
)
st.altair_chart(seasonal_chart, width="stretch")

st.caption("Recent data is provisional (subject to USGS revision).")
