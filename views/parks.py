"""Portland parks — how many, how big, and where they are."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🌳 Parks")
st.caption(
    "Portland Parks & Recreation park boundaries (PortlandMaps). Sized by acreage "
    "and mapped by centroid. Portland publishes no park-level water-feature "
    "attribute, so — unlike the Las Vegas original — there's no water flag here."
)

# --- KPIs ---
kpi = query(
    """
    select
        count(*)       as parks,
        sum(acres)     as acres,
        max(acres)     as largest
    from main.mart_parks
    """
)
largest = query("select name, acres from main.mart_parks order by acres desc limit 1")
c1, c2, c3 = st.columns(3)
c1.metric("Parks", f"{int(kpi['parks'][0]):,}")
c2.metric("Total acreage", f"{kpi['acres'][0]:,.0f} ac")
c3.metric("Largest park", f"{largest['name'][0]} ({largest['acres'][0]:,.0f} ac)")

st.divider()

# --- Size distribution ---
st.subheader("Parks by size")
by_size = query(
    """
    select size_class, count(*) as park_count, sum(acres) as total_acres
    from main.mart_parks
    group by 1
    order by 1
    """
)
size_chart = (
    alt.Chart(by_size)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2e8b57")
    .encode(
        x=alt.X("park_count:Q", title="Parks"),
        y=alt.Y("size_class:N", sort="x", title=None),
        tooltip=[
            alt.Tooltip("size_class:N", title="Size"),
            alt.Tooltip("park_count:Q", title="Parks", format=","),
            alt.Tooltip("total_acres:Q", title="Acres", format=",.0f"),
        ],
    )
)
st.altair_chart(size_chart, width="stretch")

# --- Map: park centroids sized by acreage ---
st.subheader("Where the parks are")
st.caption("Each dot is a park centroid; larger dots are larger parks.")
points = query(
    """
    select name, acres, longitude, latitude
    from main.mart_parks
    where has_valid_point
    """
)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=points,
    get_position="[longitude, latitude]",
    get_radius="sqrt(acres) * 40 + 60",
    get_fill_color=[46, 139, 87, 160],
    pickable=True,
)
view_state = pdk.ViewState(
    longitude=float(points["longitude"].mean()),
    latitude=float(points["latitude"].mean()),
    zoom=10,
    pitch=0,
)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{name}\n{acres} acres"},
    )
)

# --- Searchable table ---
st.subheader("All parks")
st.dataframe(
    query("select name, round(acres, 2) as acres from main.mart_parks order by acres desc"),
    width="stretch",
    hide_index=True,
)
