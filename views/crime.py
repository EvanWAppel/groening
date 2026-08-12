"""Portland reported crime — PPB open data (rolling 12-month window)."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🚨 Reported Crime")
st.caption(
    "Portland Police Bureau reported offenses over the trailing 12 months "
    "(PortlandMaps). Locations are offset to the 100-block; some sensitive "
    "offenses are withheld from the map."
)

# --- KPIs ---
cats = query(
    "select crime_against, sum(offense_count) as n from main.mart_crime_by_type group by 1"
)
total = int(cats["n"].sum())
cat_map = dict(zip(cats["crime_against"], cats["n"]))
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total offenses", f"{total:,}")
c2.metric("Against property", f"{int(cat_map.get('Property', 0)):,}")
c3.metric("Against persons", f"{int(cat_map.get('Person', 0)):,}")
c4.metric("Against society", f"{int(cat_map.get('Society', 0)):,}")

st.divider()

# --- Top offense groups ---
st.subheader("Most common offenses")
by_type = query(
    "select offense_group, sum(offense_count) as n from main.mart_crime_by_type "
    "group by 1 order by n desc limit 15"
)
st.altair_chart(
    alt.Chart(by_type)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#c1121f")
    .encode(
        x=alt.X("n:Q", title="Offenses"),
        y=alt.Y("offense_group:N", sort="-x", title=None),
        tooltip=["offense_group", alt.Tooltip("n:Q", title="Offenses", format=",")],
    ),
    width="stretch",
)

# --- Hour x weekday heatmap ---
st.subheader("When crime is reported")
heat = query("select reported_weekday, reported_hour, offense_count from main.mart_crime_by_hour_weekday")
weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
st.altair_chart(
    alt.Chart(heat)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_rect()
    .encode(
        x=alt.X("reported_hour:O", title="Hour of day"),
        y=alt.Y("reported_weekday:N", sort=weekday_order, title=None),
        color=alt.Color("offense_count:Q", scale=alt.Scale(scheme="reds"), title="Offenses"),
        tooltip=[
            alt.Tooltip("reported_weekday:N", title="Day"),
            alt.Tooltip("reported_hour:O", title="Hour"),
            alt.Tooltip("offense_count:Q", title="Offenses", format=","),
        ],
    ),
    width="stretch",
)

# --- Hexbin density map ---
st.subheader("Where crime is reported")
points = query("select longitude, latitude from main.mart_crime_map")
layer = pdk.Layer(
    "HexagonLayer",
    data=points,
    get_position="[longitude, latitude]",
    radius=250,
    elevation_scale=8,
    elevation_range=[0, 1500],
    extruded=True,
    coverage=0.9,
    pickable=True,
)
view_state = pdk.ViewState(
    longitude=float(points["longitude"].mean()),
    latitude=float(points["latitude"].mean()),
    zoom=10,
    pitch=45,
)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{elevationValue} offenses"},
    )
)
