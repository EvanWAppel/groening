"""Portland's inventoried trees — species, size, and the benefits they provide."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🌲 Trees")
st.caption(
    "Portland's Parks tree inventory — every catalogued tree with its species, "
    "size, and the ecosystem benefits it provides (carbon storage, stormwater "
    "interception). A very Portland dataset."
)

# --- KPIs ---
s = query("select * from main.mart_trees_summary").iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Trees inventoried", f"{int(s['total_trees']):,}")
c2.metric("Species", f"{int(s['species_count']):,}")
c3.metric("Carbon stored", f"{s['carbon_storage_tons']:,.0f} tons")
c4.metric("Annual benefits", f"${s['annual_benefits_usd']:,.0f}")

st.divider()

# --- Top species ---
st.subheader("Most common species")
species = query(
    "select common_name, native, tree_count, avg_dbh_in from main.mart_trees_by_species "
    "order by tree_count desc limit 15"
)
sp_chart = (
    alt.Chart(species)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2e8b57")
    .encode(
        x=alt.X("tree_count:Q", title="Trees"),
        y=alt.Y("common_name:N", sort="-x", title=None),
        tooltip=[
            "common_name",
            alt.Tooltip("tree_count:Q", title="Trees", format=","),
            alt.Tooltip("avg_dbh_in:Q", title="Avg trunk dia (in)", format=".1f"),
            alt.Tooltip("native:N", title="Native"),
        ],
    )
)
st.altair_chart(sp_chart, width="stretch")

# --- Map ---
st.subheader("Where the trees are")
st.caption("Density of inventoried trees — taller/brighter hexes have more trees.")
points = query("select longitude, latitude from main.mart_trees_map")
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
        tooltip={"text": "{elevationValue} trees"},
    )
)
