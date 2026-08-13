"""Multnomah County restaurant inspections — food-facility sanitation scores."""

import altair as alt
import streamlit as st

from app_db import query

st.title("🍽️ Restaurant Inspections")
st.caption(
    "Multnomah County Environmental Health inspections of food facilities "
    "(restaurants, food carts, warehouses) over the last ~6 months, from the "
    "MyHealthDepartment portal. Restaurants and carts get a 0–100 sanitation "
    "score; violations tied to foodborne illness deduct the most. The county "
    "publishes addresses but no coordinates, so there's no map."
)

# --- KPIs ---
kpi = query(
    """
    select
        count(*)                                   as establishments,
        count(sanitation_score)                    as scored,
        round(median(sanitation_score), 0)         as median_score,
        round(100.0 * count(*) filter (where sanitation_score = 100)
              / nullif(count(sanitation_score), 0), 0) as pct_perfect
    from main.mart_inspections_recent
    """
)
total = query("select count(*) as n from main.stg_restaurant_inspections")
c1, c2, c3 = st.columns(3)
c1.metric("Establishments inspected", f"{int(kpi['establishments'][0]):,}")
c2.metric("Median score", f"{kpi['median_score'][0]:.0f}")
c3.metric("Scored 100 (most recent)", f"{kpi['pct_perfect'][0]:.0f}%")
st.caption(
    f"{int(total['n'][0]):,} inspections in the window; the median/score stats "
    "use each establishment's most recent scored inspection."
)

st.divider()

# --- Score distribution ---
st.subheader("Sanitation score distribution")
st.caption("All scored food inspections in the window, bucketed worst → best.")
dist = query(
    "select score_band, band_order, inspections from main.mart_inspections_score_dist "
    "order by band_order"
)
dist_chart = (
    alt.Chart(dist)  # ty: ignore[unresolved-attribute]  (altair dynamic mark_* stubs)
    .mark_bar(color="#2a9d8f")
    .encode(
        x=alt.X("score_band:N", title="Score", sort=alt.SortField("band_order")),
        y=alt.Y("inspections:Q", title="Inspections"),
        tooltip=[
            alt.Tooltip("score_band:N", title="Score band"),
            alt.Tooltip("inspections:Q", title="Inspections", format=","),
        ],
    )
)
st.altair_chart(dist_chart, width="stretch")

# --- Monthly volume + average score ---
st.subheader("Inspections per month")
monthly = query(
    "select month, inspections, scored, avg_score from main.mart_inspections_monthly order by month"
)
base = alt.Chart(monthly)
volume = base.mark_bar(color="#e9c46a").encode(  # ty: ignore[unresolved-attribute]
    x=alt.X("month:T", title=None),
    y=alt.Y("inspections:Q", title="Inspections"),
    tooltip=[
        alt.Tooltip("month:T", title="Month"),
        alt.Tooltip("inspections:Q", title="Inspections"),
        alt.Tooltip("avg_score:Q", title="Avg score", format=".1f"),
    ],
)
avg_line = base.mark_line(color="#264653", point=True).encode(  # ty: ignore[unresolved-attribute]
    x=alt.X("month:T", title=None),
    y=alt.Y("avg_score:Q", title="Avg score", scale=alt.Scale(zero=False)),
)
st.altair_chart(
    alt.layer(volume, avg_line).resolve_scale(y="independent"), width="stretch"
)

# --- Most recent inspection per establishment ---
st.subheader("Most recent inspection per establishment")
recent = query(
    """
    select
        establishment_name                    as "Establishment",
        sanitation_score                      as "Score",
        strftime(inspection_date, '%Y-%m-%d') as "Inspected",
        purpose                               as "Purpose",
        inspection_type                       as "Type",
        address                               as "Address",
        city                                  as "City"
    from main.mart_inspections_recent
    """
)
st.dataframe(recent, width="stretch", hide_index=True)
