"""Portland short-term rentals — Accessory Short-Term Rental permits."""

import altair as alt
import pydeck as pdk
import streamlit as st

from app_db import query

st.title("🏠 Short-Term Rentals")
st.caption(
    "Portland Accessory Short-Term Rental (ASTR) permits — the city's registry of "
    "Airbnb-type rentals (PortlandMaps). Type A = host-occupied ≤2 bedrooms; "
    "Type B = larger / non-owner-occupied."
)

# --- KPIs ---
kpi = query(
    """
    select
        count(*)                                          as total,
        count(*) filter (where permit_status = 'Active')  as active
    from main.mart_short_term_rentals
    """
)
c1, c2, c3 = st.columns(3)
c1.metric("Permits", f"{int(kpi['total'][0]):,}")
c2.metric("Active", f"{int(kpi['active'][0]):,}")
c3.metric("Active share", f"{kpi['active'][0] / kpi['total'][0] * 100:.0f}%")

st.divider()

col_l, col_r = st.columns(2)
with col_l:
    st.subheader("By permit type")
    by_type = query(
        "select permit_type, count(*) as n from main.mart_short_term_rentals group by 1 order by n desc"
    )
    st.altair_chart(
        alt.Chart(by_type)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
        .mark_bar(color="#2e8b57")
        .encode(
            x=alt.X("n:Q", title="Permits"),
            y=alt.Y("permit_type:N", sort="-x", title=None),
            tooltip=["permit_type", alt.Tooltip("n:Q", title="Permits", format=",")],
        ),
        width="stretch",
    )
with col_r:
    st.subheader("By status")
    by_status = query(
        "select permit_status, count(*) as n from main.mart_short_term_rentals group by 1 order by n desc"
    )
    st.altair_chart(
        alt.Chart(by_status)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
        .mark_bar(color="#3f88c5")
        .encode(
            x=alt.X("n:Q", title="Permits"),
            y=alt.Y("permit_status:N", sort="-x", title=None),
            tooltip=["permit_status", alt.Tooltip("n:Q", title="Permits", format=",")],
        ),
        width="stretch",
    )

# --- Map ---
st.subheader("Where the rentals are")
points = query(
    "select address, permit_type, permit_status, longitude, latitude "
    "from main.mart_short_term_rentals where has_valid_point"
)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=points,
    get_position="[longitude, latitude]",
    get_radius=80,
    get_fill_color=[232, 89, 12, 140],
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
        tooltip={"text": "{address}\n{permit_type} — {permit_status}"},
    )
)

st.subheader("All permits")
st.dataframe(
    query(
        "select application_number, address, permit_type, permit_status, issued_date "
        "from main.mart_short_term_rentals order by issued_date desc"
    ),
    width="stretch",
    hide_index=True,
)
