"""Portland's bike network — how the city built out its bikeways over time."""

import altair as alt
import streamlit as st

from app_db import query

st.title("🚲 Bike Network")
st.caption(
    "Portland's bicycle network from PBOT — segment mileage by the year it was "
    "built. Portland built much of its famous bikeway network in distinct waves; "
    "this is that growth story."
)

# --- KPIs ---
tot = query("select sum(miles) as miles, sum(segments) as segs from main.mart_bike_by_facility")
newest = query("select max(year_built) as y from main.mart_bike_by_year")
recent = query(
    "select sum(miles_built) as m from main.mart_bike_by_year where year_built >= year(current_date) - 10"
)
c1, c2, c3 = st.columns(3)
c1.metric("Active network", f"{tot['miles'][0]:,.0f} mi")
c2.metric("Segments", f"{int(tot['segs'][0]):,}")
c3.metric("Miles built (last 10 yrs)", f"{recent['m'][0]:,.0f} mi")

st.divider()

# --- Cumulative growth ---
st.subheader("Cumulative bike-network growth")
st.caption(
    "Growth reflects only segments with a recorded build year — about 567 of the "
    "3,065 current network miles are dated, so this undercounts the full network."
)
byyear = query(
    "select year_built, miles_built, cumulative_miles from main.mart_bike_by_year order by year_built"
)
cum = (
    alt.Chart(byyear)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_area(color="#2e8b57", opacity=0.7)
    .encode(
        x=alt.X("year_built:O", title=None),
        y=alt.Y("cumulative_miles:Q", title="Cumulative miles"),
        tooltip=[
            alt.Tooltip("year_built:O", title="Year"),
            alt.Tooltip("cumulative_miles:Q", title="Cumulative mi", format=",.0f"),
        ],
    )
)
st.altair_chart(cum, width="stretch")

# --- Miles built per year ---
st.subheader("Miles built per year")
built = (
    alt.Chart(byyear)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#3f88c5")
    .encode(
        x=alt.X("year_built:O", title=None),
        y=alt.Y("miles_built:Q", title="Miles built"),
        tooltip=[
            alt.Tooltip("year_built:O", title="Year"),
            alt.Tooltip("miles_built:Q", title="Miles", format=",.1f"),
        ],
    )
)
st.altair_chart(built, width="stretch")

# --- By facility type ---
st.subheader("Network by facility type")
fac = query("select facility, miles, segments from main.mart_bike_by_facility order by miles desc")
fac_chart = (
    alt.Chart(fac)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2e8b57")
    .encode(
        x=alt.X("miles:Q", title="Miles"),
        y=alt.Y("facility:N", sort="-x", title="Facility code"),
        tooltip=["facility", alt.Tooltip("miles:Q", title="Miles", format=",.1f")],
    )
)
st.altair_chart(fac_chart, width="stretch")
st.caption("Facility codes are PBOT's bike-facility type abbreviations (e.g. BL = bike lane).")
