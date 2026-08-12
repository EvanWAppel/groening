"""Portland-metro air quality — EPA AQS daily PM2.5 & Ozone (tri-county)."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("💨 Air Quality")
st.caption(
    "EPA daily PM2.5 and Ozone across the Portland tri-county metro (Multnomah, "
    "Washington, Clackamas). Higher AQI is worse; days above 100 are 'unhealthy "
    "for sensitive groups' — Portland's wildfire-smoke summers show up here."
)

# --- KPIs ---
kpi = query(
    """
    select pollutant, round(avg(avg_aqi), 0) as aqi
    from main.mart_air_quality_monthly group by 1
    """
)
aqi_by_poll = dict(zip(kpi["pollutant"], kpi["aqi"]))
worst = query(
    "select year, sum(unhealthy_days) as d from main.mart_air_quality_bad_days group by 1 order by d desc limit 1"
)
c1, c2, c3 = st.columns(3)
c1.metric("Avg PM2.5 AQI", f"{aqi_by_poll.get('PM2.5', float('nan')):.0f}")
c2.metric("Avg Ozone AQI", f"{aqi_by_poll.get('Ozone', float('nan')):.0f}")
c3.metric("Worst year (unhealthy days)", f"{int(worst['d'][0])} ({int(worst['year'][0])})")

st.info("Note: Clackamas County has an Ozone monitor but no EPA regulatory PM2.5 monitor.")

st.divider()

# --- Monthly AQI trend by pollutant ---
st.subheader("Monthly average AQI")
monthly = query("select month, pollutant, avg_aqi from main.mart_air_quality_monthly order by month")
trend = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_line()
    .encode(
        x=alt.X("month:T", title=None),
        y=alt.Y("avg_aqi:Q", title="Avg AQI"),
        color=alt.Color("pollutant:N", title="Pollutant"),
        tooltip=[
            alt.Tooltip("month:T", title="Month"),
            alt.Tooltip("pollutant:N", title="Pollutant"),
            alt.Tooltip("avg_aqi:Q", title="Avg AQI", format=".0f"),
        ],
    )
)
st.altair_chart(trend, width="stretch")

# --- Unhealthy days per year ---
st.subheader("Unhealthy-air days per year (any site AQI > 100)")
bad = query("select year, pollutant, unhealthy_days from main.mart_air_quality_bad_days order by year")
bad_chart = (
    alt.Chart(bad)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar()
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("unhealthy_days:Q", title="Unhealthy days"),
        color=alt.Color("pollutant:N", title="Pollutant"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("pollutant:N", title="Pollutant"),
            alt.Tooltip("unhealthy_days:Q", title="Days"),
        ],
    )
)
st.altair_chart(bad_chart, width="stretch")

# --- Monitor map ---
st.subheader("Monitoring sites")
sites = query(
    "select site_name, county, pollutant, avg_aqi, longitude, latitude "
    "from main.mart_air_quality_by_site"
)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=sites,
    get_position="[longitude, latitude]",
    get_radius="avg_aqi * 30 + 150",
    get_fill_color=[193, 18, 31, 150],
    pickable=True,
)
view_state = pdk.ViewState(
    longitude=float(sites["longitude"].mean()),
    latitude=float(sites["latitude"].mean()),
    zoom=9,
    pitch=0,
)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "{site_name} ({county})\n{pollutant} avg AQI {avg_aqi}"},
    )
)

st.subheader("Sites")
st.dataframe(sites.drop(columns=["longitude", "latitude"]), width="stretch", hide_index=True)
