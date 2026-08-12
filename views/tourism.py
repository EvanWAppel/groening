"""PDX air travel — international passenger volumes (BTS)."""

import altair as alt
import streamlit as st

from app_db import query

st.title("✈️ Air Travel")
st.caption(
    "International passenger volumes at Portland International Airport (PDX), "
    "monthly since 1990 (US BTS). Portland has no gaming/tourism analog to Las "
    "Vegas, so this reframes the tourism page around air travel — and the 2020 "
    "COVID collapse is impossible to miss."
)

# --- KPIs ---
full_years = query("select * from main.mart_tourism_annual where months_reported = 12 order by year")
latest = full_years.iloc[-1]
peak = full_years.loc[full_years["passengers"].idxmax()]
# 2020 lost a month or two of intl service, so pull it straight from the annual
# mart rather than the complete-year filter.
covid_2020 = query("select passengers from main.mart_tourism_annual where year = 2020")
c1, c2, c3 = st.columns(3)
c1.metric(f"Intl passengers ({int(latest['year'])})", f"{int(latest['passengers']):,}")
c2.metric("Peak year", f"{int(peak['passengers']):,} ({int(peak['year'])})")
if not covid_2020.empty:
    p2020 = int(covid_2020["passengers"].iloc[0])
    drop = (1 - p2020 / peak["passengers"]) * 100
    c3.metric("2020 vs peak", f"−{drop:.0f}%", delta=f"{p2020:,} in 2020")

st.divider()

# --- Monthly series (COVID crash) ---
st.subheader("Monthly international passengers")
monthly = query("select month_date, passengers from main.mart_tourism_monthly order by month_date")
line = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_area(color="#3f88c5", opacity=0.7)
    .encode(
        x=alt.X("month_date:T", title=None),
        y=alt.Y("passengers:Q", title="Passengers / month"),
        tooltip=[
            alt.Tooltip("month_date:T", title="Month"),
            alt.Tooltip("passengers:Q", title="Passengers", format=","),
        ],
    )
)
st.altair_chart(line, width="stretch")

# --- Annual ---
st.subheader("International passengers per year")
annual_chart = (
    alt.Chart(full_years)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2e8b57")
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("passengers:Q", title="Passengers"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("passengers:Q", title="Passengers", format=","),
        ],
    )
)
st.altair_chart(annual_chart, width="stretch")
st.caption("International passengers only (domestic not included in the BTS series).")
