"""Portland's Historic Resource Inventory — surveyed historic buildings and sites."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query
from ui import page_header

page_header("historic")
st.caption(
    "The City's Historic Resource Inventory — thousands of surveyed historic "
    "buildings and sites, each with an architectural style, a significance rank "
    "(I is highest), and an approximate year built. A map of Portland's built past."
)

# --- KPIs ---
s = query("select * from main.mart_historic_summary").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Resources", f"{int(s['total_resources']):,}")
c2.metric("Highly significant", f"{int(s['significant_count']):,}")
c3.metric("Architectural styles", f"{int(s['style_count']):,}")
c4.metric("Oldest", f"{int(s['oldest_year'])}")

st.divider()

# --- By decade built ---
st.subheader("When they were built")
by_decade = query("select decade, resources from main.mart_historic_by_decade order by decade")
decade_chart = (
    alt.Chart(by_decade)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#a0522d")
    .encode(
        x=alt.X("decade:O", title="Decade built"),
        y=alt.Y("resources:Q", title="Resources"),
        tooltip=[
            alt.Tooltip("decade:O", title="Decade"),
            alt.Tooltip("resources:Q", title="Resources", format=","),
        ],
    )
)
st.altair_chart(decade_chart, width="stretch")

# --- By style and by rank ---
left, right = st.columns(2)
with left:
    st.subheader("Top architectural styles")
    styles = query(
        "select style, resources from main.mart_historic_by_style order by resources desc limit 12"
    )
    style_chart = (
        alt.Chart(styles)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
        .mark_bar(color="#346653")
        .encode(
            x=alt.X("resources:Q", title="Resources"),
            y=alt.Y("style:N", sort="-x", title=None),
            tooltip=["style", alt.Tooltip("resources:Q", title="Resources", format=",")],
        )
    )
    st.altair_chart(style_chart, width="stretch")
with right:
    st.subheader("By significance rank")
    ranks = query(
        "select significance_rank, resources from main.mart_historic_by_rank order by resources desc"
    )
    rank_chart = (
        alt.Chart(ranks)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
        .mark_bar(color="#4a6fa5")
        .encode(
            x=alt.X("resources:Q", title="Resources"),
            y=alt.Y("significance_rank:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("significance_rank:N", title="Rank"),
                alt.Tooltip("resources:Q", title="Resources", format=","),
            ],
        )
    )
    st.altair_chart(rank_chart, width="stretch")

# --- Map ---
st.subheader("Where the historic resources are")
st.caption("Density of surveyed historic resources — taller/brighter hexes have more.")
points = query("select longitude, latitude from main.mart_historic_map")
layer = pdk.Layer(
    "HexagonLayer",
    data=points,
    get_position="[longitude, latitude]",
    radius=150,
    elevation_scale=4,
    elevation_range=[0, 1000],
    extruded=True,
    coverage=0.9,
    pickable=True,
)
view_state = pdk.ViewState(
    longitude=float(points["longitude"].mean()),
    latitude=float(points["latitude"].mean()),
    zoom=11,
    pitch=45,
)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{elevationValue} historic resources"},
    )
)
st.caption("Source: City of Portland Historic Resource Inventory (PortlandMaps).")
