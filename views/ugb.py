"""Metro Urban Growth Boundary — Oregon's signature land-use line."""

import json

import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🗺️ Urban Growth Boundary")
st.caption(
    "The Metro Urban Growth Boundary (UGB) — the line, unique to Oregon, that "
    "separates urban land from rural/farm land across the Portland tri-county "
    "region. Development is concentrated inside it to curb sprawl."
)

row = query("select area_sqmi, boundary_json from main.mart_ugb").iloc[0]
ring = json.loads(row["boundary_json"])

c1, c2 = st.columns(2)
c1.metric("UGB area", f"{row['area_sqmi']:,.0f} sq mi")
c2.metric("Counties spanned", "Multnomah · Washington · Clackamas")

st.divider()

st.subheader("The boundary")
lons = [p[0] for p in ring]
lats = [p[1] for p in ring]
path_layer = pdk.Layer(
    "PathLayer",
    data=[{"path": ring}],
    get_path="path",
    get_color=[46, 139, 87],
    get_width=60,
    width_min_pixels=2,
)
view_state = pdk.ViewState(
    longitude=sum(lons) / len(lons),
    latitude=sum(lats) / len(lats),
    zoom=8,
    pitch=0,
)
st.pydeck_chart(pdk.Deck(layers=[path_layer], initial_view_state=view_state))
st.caption(
    "Source: Metro Data Resource Center (RLIS). This is the current boundary; "
    "Metro publishes no single machine-readable amendment history, so an "
    "expansion-over-time view is not shown."
)
