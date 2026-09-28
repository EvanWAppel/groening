"""Portland service requests — graffiti + pothole reports (311-style)."""

import altair as alt
import streamlit as st

from app_db import query
from ui import neighborhood_choropleth, page_header

page_header("service_requests")
st.caption(
    "Portland publishes no single 311 feed, so this page combines the two "
    "non-sensitive request layers the City does publish on PortlandMaps: graffiti "
    "reports (Bureau of Planning & Sustainability, since Sept 2022) and pothole "
    "reports (PBOT, rolling last 12 months)."
)

# Graffiti in the brand's rust, potholes in asphalt slate.
TYPE_COLORS = {"Graffiti": "#b8492e", "Pothole": "#4a5a6a"}
ACCENTS = {"Graffiti": (184, 73, 46), "Pothole": (74, 90, 106)}
type_scale = alt.Scale(domain=list(TYPE_COLORS), range=list(TYPE_COLORS.values()))

# --- KPIs ---
summary = query("select * from main.mart_service_requests_summary").set_index("request_type")
graffiti, pothole = summary.loc["Graffiti"], summary.loc["Pothole"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Graffiti reports", f"{int(graffiti['total_requests']):,}")
c2.metric("Graffiti still open", f"{int(graffiti['open_requests']):,}")
c3.metric("Pothole reports", f"{int(pothole['total_requests']):,}")
c4.metric("Potholes still open", f"{int(pothole['open_requests']):,}")
st.caption(
    f"Graffiti {graffiti['first_date']:%b %Y} – {graffiti['last_date']:%b %Y} · "
    f"potholes {pothole['first_date']:%b %Y} – {pothole['last_date']:%b %Y}."
)

st.divider()

# --- Monthly volume ---
st.subheader("Reports per month")
monthly = query(
    "select month, request_type, request_count from main.mart_service_requests_monthly order by month"
)
st.altair_chart(
    alt.Chart(monthly)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_line(point=True)
    .encode(
        x=alt.X("month:T", title=None),
        y=alt.Y("request_count:Q", title="Reports"),
        color=alt.Color("request_type:N", scale=type_scale, title=None),
        tooltip=[
            alt.Tooltip("month:T", title="Month", format="%b %Y"),
            alt.Tooltip("request_type:N", title="Type"),
            alt.Tooltip("request_count:Q", title="Reports", format=","),
        ],
    ),
    width="stretch",
)

# --- Graffiti resolution ---
st.subheader("How graffiti reports were resolved")
st.caption("The City's free-text graffiti status, grouped into outcomes.")
resolution = query(
    "select resolution, request_count from main.mart_graffiti_resolution order by request_count desc"
)
st.altair_chart(
    alt.Chart(resolution)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color=TYPE_COLORS["Graffiti"])
    .encode(
        x=alt.X("request_count:Q", title="Reports"),
        y=alt.Y("resolution:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("resolution:N", title="Outcome"),
            alt.Tooltip("request_count:Q", title="Reports", format=","),
        ],
    ),
    width="stretch",
)

# --- Choropleth: requests by neighborhood, one request type at a time ---
st.subheader("Where requests come from")
kind = st.segmented_control(
    "Request type", list(TYPE_COLORS), default="Graffiti", label_visibility="collapsed"
) or "Graffiti"
st.caption(
    f"{kind} reports by neighborhood"
    + (" since Sept 2022." if kind == "Graffiti" else " over the last 12 months.")
)
hoods = query(
    "select request_type, neighborhood, boundary_json, n from main.mart_service_requests_choropleth"
)
neighborhood_choropleth(
    hoods[hoods["request_type"] == kind], value_label="reports", accent=ACCENTS[kind]
)
