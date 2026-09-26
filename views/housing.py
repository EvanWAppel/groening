"""Portland's regulated affordable housing — the Housing Bureau's portfolio."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query
from ui import page_header

page_header("housing")
st.caption(
    "The Portland Housing Bureau's portfolio of financed, income-regulated "
    "affordable rental housing — every project with its unit count, building type, "
    "and location. 'Regulated' units carry income/affordability restrictions."
)

# --- KPIs ---
s = query("select * from main.mart_housing_summary").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Projects", f"{int(s['total_projects']):,}")
c2.metric("Regulated units", f"{int(s['regulated_units']):,}")
c3.metric("Total units", f"{int(s['total_units']):,}")

st.divider()

# --- Regulated units completed per year ---
st.subheader("Regulated units completed per year")
by_year = query("select year, regulated_units from main.mart_housing_by_year order by year")
year_chart = (
    alt.Chart(by_year)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#a0522d")
    .encode(
        x=alt.X("year:O", title="Year completed"),
        y=alt.Y("regulated_units:Q", title="Regulated units"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("regulated_units:Q", title="Regulated units", format=","),
        ],
    )
)
st.altair_chart(year_chart, width="stretch")

# --- By building type ---
st.subheader("By building type")
by_type = query(
    "select building_type, projects, regulated_units from main.mart_housing_by_type "
    "order by regulated_units desc"
)
type_chart = (
    alt.Chart(by_type)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#4a6fa5")
    .encode(
        x=alt.X("regulated_units:Q", title="Regulated units"),
        y=alt.Y("building_type:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("building_type:N", title="Type"),
            alt.Tooltip("projects:Q", title="Projects", format=","),
            alt.Tooltip("regulated_units:Q", title="Regulated units", format=","),
        ],
    )
)
st.altair_chart(type_chart, width="stretch")

# --- Map ---
st.subheader("Where the affordable housing is")
st.caption("Each project sized by its regulated unit count.")
points = query(
    "select project_name, longitude, latitude, regulated_units from main.mart_housing_map"
)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=points,
    get_position="[longitude, latitude]",
    get_radius="regulated_units",
    radius_scale=3,
    radius_min_pixels=3,
    radius_max_pixels=40,
    get_fill_color=[160, 82, 45, 160],
    pickable=True,
)
view_state = pdk.ViewState(
    longitude=float(points["longitude"].mean()),
    latitude=float(points["latitude"].mean()),
    zoom=11,
    pitch=0,
)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{project_name}\n{regulated_units} regulated units"},
    )
)
st.caption("Source: Portland Housing Bureau Rental Portfolio (PortlandMaps).")
