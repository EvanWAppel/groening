"""Portland residential building permits — volume, valuation, and where they land."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🏗️ Building Permits")
st.caption(
    "PortlandMaps residential building-permit history (since 1995), with "
    "construction valuations and new-unit counts. A window on the city's "
    "building cycles and where growth is concentrated."
)

# --- KPIs ---
kpi = query(
    """
    select
        sum(permit_count)     as permits,
        sum(total_valuation)  as valuation,
        sum(total_new_units)  as new_units
    from main.mart_permits_monthly
    """
)
span = query(
    "select min(issue_month) as first, max(issue_month) as last from main.mart_permits_monthly"
)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Permits issued", f"{int(kpi['permits'][0]):,}")
c2.metric("Total valuation", f"${kpi['valuation'][0] / 1e9:.1f}B")
c3.metric("New units", f"{int(kpi['new_units'][0]):,}")
c4.metric("Period", f"{span['first'][0]:%Y} – {span['last'][0]:%Y}")

st.divider()

# --- Monthly permits + valuation ---
monthly = query(
    """
    select issue_month, permit_count, total_valuation
    from main.mart_permits_monthly
    order by 1
    """
)
st.subheader("Permits issued per month")
permits_line = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_area(color="#2e8b57", opacity=0.7)
    .encode(
        x=alt.X("issue_month:T", title=None),
        y=alt.Y("permit_count:Q", title="Permits"),
        tooltip=[
            alt.Tooltip("issue_month:T", title="Month"),
            alt.Tooltip("permit_count:Q", title="Permits", format=","),
        ],
    )
)
st.altair_chart(permits_line, width="stretch")

st.subheader("Construction valuation per month")
val_line = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_line(color="#3f88c5")
    .encode(
        x=alt.X("issue_month:T", title=None),
        y=alt.Y("total_valuation:Q", title="Valuation ($)", axis=alt.Axis(format="~s")),
        tooltip=[
            alt.Tooltip("issue_month:T", title="Month"),
            alt.Tooltip("total_valuation:Q", title="Valuation", format="$,.0f"),
        ],
    )
)
st.altair_chart(val_line, width="stretch")

# --- By work class ---
by_type = query(
    """
    select work_class, permit_count, total_valuation
    from main.mart_permits_by_type
    order by permit_count desc
    limit 15
    """
)
st.subheader("Permits by work class")
type_chart = (
    alt.Chart(by_type)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2e8b57")
    .encode(
        x=alt.X("permit_count:Q", title="Permits"),
        y=alt.Y("work_class:N", sort="-x", title=None),
        tooltip=[
            "work_class",
            alt.Tooltip("permit_count:Q", title="Permits", format=","),
            alt.Tooltip("total_valuation:Q", title="Valuation", format="$,.0f"),
        ],
    )
)
st.altair_chart(type_chart, width="stretch")
st.dataframe(by_type, width="stretch", hide_index=True)

st.divider()

# --- Where permits land (PyDeck hexbin over the geocoded permits) ---
st.subheader("Where permits are issued")
st.caption("Hexbin density of geocoded permits across the city — taller/brighter = more permits.")
points = query(
    """
    select longitude, latitude
    from main.mart_permits_map
    """
)
layer = pdk.Layer(
    "HexagonLayer",
    data=points,
    get_position="[longitude, latitude]",
    radius=200,
    elevation_scale=6,
    elevation_range=[0, 1200],
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
        tooltip={"text": "{elevationValue} permits"},
    )
)
