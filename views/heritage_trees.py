"""Portland's Heritage Trees — individually designated, protected landmark trees."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query
from ui import page_header

page_header("heritage_trees")
st.caption(
    "Portland formally designates individual **Heritage Trees** — specimens of "
    "exceptional size, age, or species that gain city protection. A different "
    "thing from the bulk street-tree inventory: these are named landmarks, "
    "designated one at a time since 1973."
)

# --- KPIs ---
s = query("select * from main.mart_heritage_summary").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Heritage trees", f"{int(s['total_trees']):,}")
c2.metric("Species", f"{int(s['species_count']):,}")
c3.metric("Designating since", f"{int(s['first_year'])}")
c4.metric("Largest trunk", f"{int(s['max_diameter_in'])} in")

st.divider()

# --- Designations per year ---
st.subheader("Designations per year")
by_year = query("select year, designated from main.mart_heritage_by_year order by year")
year_chart = (
    alt.Chart(by_year)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#346653")
    .encode(
        x=alt.X("year:O", title="Year designated"),
        y=alt.Y("designated:Q", title="Trees designated"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("designated:Q", title="Designated"),
        ],
    )
)
st.altair_chart(year_chart, width="stretch")

# --- Top species ---
st.subheader("Most-designated species")
species = query(
    "select common_name, tree_count, avg_diameter_in from main.mart_heritage_by_species "
    "order by tree_count desc limit 15"
)
sp_chart = (
    alt.Chart(species)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#4a6fa5")
    .encode(
        x=alt.X("tree_count:Q", title="Heritage trees"),
        y=alt.Y("common_name:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("common_name:N", title="Species"),
            alt.Tooltip("tree_count:Q", title="Trees"),
            alt.Tooltip("avg_diameter_in:Q", title="Avg trunk dia (in)", format=".1f"),
        ],
    )
)
st.altair_chart(sp_chart, width="stretch")

# --- Map ---
st.subheader("Where the heritage trees stand")
st.caption("Each designated tree, sized by trunk diameter.")
points = query(
    "select common_name, neighborhood, diameter_in, longitude, latitude "
    "from main.mart_heritage_map"
)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=points,
    get_position="[longitude, latitude]",
    get_radius="diameter_in",
    radius_scale=6,
    radius_min_pixels=3,
    radius_max_pixels=40,
    get_fill_color=[52, 102, 83, 170],
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
        tooltip={"text": "{common_name}\n{neighborhood} · {diameter_in} in trunk"},
    )
)
st.caption("Source: Portland Parks & Recreation Urban Forestry — Heritage Trees (PortlandMaps).")
