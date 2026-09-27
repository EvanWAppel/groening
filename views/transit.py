"""TriMet transit — routes by mode and the stops that stitch the region together."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query
from ui import page_header

page_header("transit")
st.caption(
    "The region's transit network as TriMet publishes it in the GTFS standard: "
    "every route, its mode, and every boardable stop. Bus, MAX light rail, WES "
    "commuter rail, and the Portland Aerial Tram all ride in one feed."
)

# --- KPIs ---
s = query("select * from main.mart_transit_summary").iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric("Routes", f"{int(s['total_routes']):,}")
c2.metric("Stops", f"{int(s['total_stops']):,}")
c3.metric("Modes", f"{int(s['total_modes']):,}")

st.divider()

# --- Routes by mode ---
st.subheader("Routes by mode")
by_mode = query("select mode, route_count from main.mart_transit_by_mode order by route_count desc")
mode_chart = (
    alt.Chart(by_mode)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#4a6fa5")
    .encode(
        x=alt.X("route_count:Q", title="Routes"),
        y=alt.Y("mode:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("mode:N", title="Mode"),
            alt.Tooltip("route_count:Q", title="Routes", format=","),
        ],
    )
)
st.altair_chart(mode_chart, width="stretch")

# --- Stops map ---
st.subheader("Where you can board")
st.caption("Every boardable TriMet stop, drawn flat — the shape of the network itself.")
points = query("select longitude, latitude from main.mart_transit_stops_map")
layer = pdk.Layer(
    "ScatterplotLayer",
    data=points,
    get_position="[longitude, latitude]",
    get_fill_color=[46, 110, 74, 140],
    get_radius=60,
    radius_min_pixels=1.5,
    pickable=False,
)
view_state = pdk.ViewState(
    longitude=float(points["longitude"].mean()),
    latitude=float(points["latitude"].mean()),
    zoom=10,
    pitch=0,
)
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))

# --- Route list ---
st.subheader("Every route")
routes = query(
    "select route_short_name, route_long_name, mode from main.mart_transit_routes "
    "order by mode, route_short_name"
)
st.dataframe(
    routes,
    hide_index=True,
    width="stretch",
    column_config={
        "route_short_name": st.column_config.TextColumn("Route"),
        "route_long_name": st.column_config.TextColumn("Name", width="large"),
        "mode": st.column_config.TextColumn("Mode"),
    },
)
st.caption("Source: TriMet GTFS static feed (routes.txt, stops.txt).")
