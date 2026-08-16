"""Overview: the landing page tying every Portland-metro dataset together.

A navigational hub: one headline number per topic, each linking to its page.
Numbers come straight from the dbt marts the other pages already read.
"""

import streamlit as st

from app_db import query

st.title("🌲 Portland Open-Data Explorer")
st.caption(
    "Public data from the City of Portland, Multnomah County, Metro, and federal "
    "sources, loaded into DuckDB, modeled with dbt, and served with Streamlit. "
    "Thirteen datasets, from building permits to river flow. Pick a tile to dig in."
)

# --- Headline numbers, one query per topic (cached by app_db.query) ---
permits = query(
    "select sum(permit_count) as n, sum(total_valuation) as v from main.mart_permits_monthly"
)
parks = query("select count(*) as n, sum(acres) as acres from main.mart_parks")
crime = query("select sum(offense_count) as n from main.mart_crime_by_type")
str_ = query("select count(*) as n from main.mart_short_term_rentals")
insp = query(
    "select sum(avg_score * scored) / sum(scored) as avg_score from main.mart_inspections_monthly"
)
river = query("select avg(avg_cfs) as cfs from main.mart_willamette_monthly")
rain = query("select avg(total_precip_in) as inches from main.mart_weather_annual")
air = query(
    "select year, sum(unhealthy_days) as days from main.mart_air_quality_bad_days "
    "group by year order by year desc limit 1"
)
trees = query("select total_trees, annual_benefits_usd from main.mart_trees_summary")
bike = query(
    "select cumulative_miles as miles from main.mart_bike_by_year order by year_built desc limit 1"
)
tourism = query(
    "select year, passengers from main.mart_tourism_annual "
    "where months_reported = 12 order by year desc limit 1"
)
marriage = query(
    "select year, total from main.mart_marriage_annual "
    "where not preliminary order by year desc limit 1"
)
ugb = query("select area_sqmi from main.mart_ugb")

# --- Topic tiles: (page, icon, title, headline value, sub-caption) ---
tiles = [
    (
        "views/building_permits.py",
        "🏗️",
        "Building Permits",
        f"{int(permits['n'][0]):,}",
        f"${permits['v'][0] / 1e9:.1f}B declared value",
    ),
    (
        "views/parks.py",
        "🌳",
        "Parks",
        f"{int(parks['n'][0]):,}",
        f"{parks['acres'][0]:,.0f} acres of parkland",
    ),
    (
        "views/crime.py",
        "🚨",
        "Reported Crime",
        f"{int(crime['n'][0]):,}",
        "offenses, rolling 12 months",
    ),
    (
        "views/short_term_rentals.py",
        "🏠",
        "Short-Term Rentals",
        f"{int(str_['n'][0]):,}",
        "registered STR permits",
    ),
    (
        "views/restaurant_inspections.py",
        "🍽️",
        "Restaurant Inspections",
        f"{insp['avg_score'][0]:.0f}/100",
        "avg sanitation score, last 6 mo",
    ),
    (
        "views/willamette.py",
        "🌊",
        "Willamette River",
        f"{river['cfs'][0]:,.0f}",
        "cfs average discharge",
    ),
    (
        "views/weather.py",
        "🌧️",
        "Rain & Records",
        f"{rain['inches'][0]:.0f} in",
        "average rainfall per year",
    ),
    (
        "views/air_quality.py",
        "💨",
        "Air Quality",
        f"{int(air['days'][0]):,}",
        f"unhealthy-air days in {int(air['year'][0])}",
    ),
    (
        "views/trees.py",
        "🌲",
        "Trees",
        f"{int(trees['total_trees'][0]):,}",
        f"${trees['annual_benefits_usd'][0] / 1e6:.1f}M annual benefits",
    ),
    (
        "views/bike.py",
        "🚲",
        "Bike Network",
        f"{bike['miles'][0]:,.0f} mi",
        "of bikeway built to date",
    ),
    (
        "views/tourism.py",
        "✈️",
        "Air Travel",
        f"{tourism['passengers'][0] / 1e6:.1f}M",
        f"PDX int'l passengers in {int(tourism['year'][0])}",
    ),
    (
        "views/marriage.py",
        "💍",
        "Marriages",
        f"{int(marriage['total'][0]):,}",
        f"licenses issued in {int(marriage['year'][0])}",
    ),
    (
        "views/ugb.py",
        "🗺️",
        "Urban Growth Boundary",
        f"{ugb['area_sqmi'][0]:,.0f} mi²",
        "inside Metro's growth boundary",
    ),
]

st.divider()

# 4 tiles per row; each is a bordered card with a headline metric + page link.
per_row = 4
for start in range(0, len(tiles), per_row):
    cols = st.columns(per_row)
    for col, (page, icon, title, value, sub) in zip(cols, tiles[start : start + per_row]):
        with col.container(border=True):
            st.metric(f"{icon} {title}", value)
            st.caption(sub)
            st.page_link(page, label="Explore →")

st.divider()
about, links = st.columns([3, 2])
with about:
    st.caption(
        "The same pipeline runs on Las Vegas and Seattle data: the only difference "
        "is one `city_config.py` file. ELT into DuckDB, dbt staging and marts, "
        "Streamlit with Altair and PyDeck. Each dataset's source is noted on its page."
    )
with links:
    st.caption(
        "Built by Evan Appel with agentic tooling, kept honest with tests. "
        "[Portfolio](https://evanappel.me/projects) · "
        "[GitHub](https://github.com/EvanWAppel/groening) · "
        "[LinkedIn](https://www.linkedin.com/in/evanwebsterappel)"
    )
