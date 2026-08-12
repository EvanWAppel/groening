"""Portland weather — Rain & Records (NOAA GHCN-Daily at PDX, since 1938)."""

import altair as alt
import streamlit as st

from app_db import query

st.title("🌧️ Rain & Records")
st.caption(
    "Nearly 90 years of daily weather at Portland International Airport "
    "(NOAA GHCN-Daily). Portland is temperate, not extreme — except when it is."
)

# --- KPIs ---
ann = query("select avg(total_precip_in) as avg_rain from main.mart_weather_annual")
ext = query(
    "select max(record_high_f) as hi, min(record_low_f) as lo from main.mart_weather_annual"
)
wet = query("select obs_date, precip_in from main.mart_weather_wettest_days order by precip_in desc limit 1")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Avg yearly rain", f"{ann['avg_rain'][0]:.1f} in")
c2.metric("Record high", f"{ext['hi'][0]:.0f}°F")
c3.metric("Record low", f"{ext['lo'][0]:.0f}°F")
c4.metric("Wettest day", f"{wet['precip_in'][0]:.2f} in ({wet['obs_date'][0]:%Y})")

st.divider()

# --- Monthly climatology: rainfall ---
st.subheader("Average rainfall by month")
monthly = query(
    "select month_num, month_name, avg_precip_in, avg_tmax_f, avg_tmin_f "
    "from main.mart_weather_monthly order by month_num"
)
rain_chart = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#3f88c5")
    .encode(
        x=alt.X("month_name:N", sort=list(monthly["month_name"]), title=None),
        y=alt.Y("avg_precip_in:Q", title="Avg precip (in)"),
        tooltip=[
            alt.Tooltip("month_name:N", title="Month"),
            alt.Tooltip("avg_precip_in:Q", title="Avg precip (in)", format=".2f"),
        ],
    )
)
st.altair_chart(rain_chart, width="stretch")

# --- Monthly climatology: temperature band ---
st.subheader("Typical high / low temperature by month")
_month_sort = list(monthly["month_name"])
tmax_line = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_line(color="#e8590c")
    .encode(
        x=alt.X("month_name:N", sort=_month_sort, title=None),
        y=alt.Y("avg_tmax_f:Q", title="°F"),
        tooltip=[alt.Tooltip("avg_tmax_f:Q", title="Avg high", format=".0f")],
    )
)
tmin_line = (
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_line(color="#3f88c5")
    .encode(
        x=alt.X("month_name:N", sort=_month_sort, title=None),
        y=alt.Y("avg_tmin_f:Q", title="°F"),
        tooltip=[alt.Tooltip("avg_tmin_f:Q", title="Avg low", format=".0f")],
    )
)
st.altair_chart(tmax_line + tmin_line, width="stretch")

# --- Annual rainfall trend ---
st.subheader("Total rainfall per year")
annual = query(
    "select year, total_precip_in, rainy_days from main.mart_weather_annual order by year"
)
year_chart = (
    alt.Chart(annual)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2e8b57")
    .encode(
        x=alt.X("year:O", title=None),
        y=alt.Y("total_precip_in:Q", title="Total precip (in)"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("total_precip_in:Q", title="Rain (in)", format=".1f"),
            alt.Tooltip("rainy_days:Q", title="Rainy days"),
        ],
    )
)
st.altair_chart(year_chart, width="stretch")

# --- Wettest days ---
st.subheader("Wettest days on record")
st.dataframe(
    query(
        "select obs_date as date, precip_in as \"precip (in)\" "
        "from main.mart_weather_wettest_days order by precip_in desc"
    ),
    width="stretch",
    hide_index=True,
)
