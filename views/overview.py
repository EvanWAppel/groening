"""A browsable field guide to fifteen Portland public datasets."""

from base64 import b64encode
from html import escape
from pathlib import Path

import streamlit as st

from app_db import query
from ui import ASSETS, TOPICS

art = b64encode((ASSETS / "portland.svg").read_bytes()).decode("ascii")
st.html(f'''<section class="hero">
    <div><div class="eyebrow">An atlas of everyday life · No. 01</div>
    <h1>A city, by<br>the <em>numbers.</em></h1>
    <p class="hero-copy">Beyond the bridges and the rain, there’s a story in every record.
    Explore the data that shapes Portland — from its tree canopy to its changing streets.</p>
    <a class="hero-link" href="#datasets">Find your perspective <span>↓</span></a></div>
    <figure class="hero-art"><img src="data:image/svg+xml;base64,{art}"
    alt="Illustrated Portland: forest contours, a street grid, and bridges across the Willamette River.">
    <figcaption><span>FIG. 01 — BETWEEN FOREST &amp; RIVER</span>
    <span>SCHEMATIC / NOT TO SCALE</span></figcaption></figure>
    </section>
    <div class="index-strip"><span><span class="status-dot"></span>PUBLIC DATA, SHARED KNOWLEDGE</span>
    <span><b>15</b> DATASETS &nbsp; / &nbsp; <b>01</b> CITY</span>
    <span class="strip-territory">PORTLAND &amp; THE METRO REGION</span></div>''')

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
transit = query("select total_routes, total_stops from main.mart_transit_summary")
housing = query("select total_projects, regulated_units from main.mart_housing_summary")

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
    (
        "views/transit.py",
        "🚆",
        "Transit",
        f"{int(transit['total_stops'][0]):,}",
        f"boardable stops on {int(transit['total_routes'][0])} routes",
    ),
    (
        "views/housing.py",
        "🏘️",
        "Affordable Housing",
        f"{int(housing['regulated_units'][0]):,}",
        f"regulated units across {int(housing['total_projects'][0])} projects",
    ),
]


st.html('<div class="collection-heading" id="datasets"><h2>The city, in detail.</h2>'
        '<span>EXPLORE THE COLLECTION ↙</span></div>')
filters, search = st.columns([2, 1], vertical_alignment="bottom")
with filters:
    category = st.pills(
        "Browse by theme", ["All datasets", "The natural city", "The built city", "Everyday life"],
        default="All datasets", label_visibility="collapsed",
    )
with search:
    term = st.text_input("Search datasets", placeholder="Search the collection…",
                         label_visibility="collapsed", icon=":material/search:")

visible = [
    tile for tile in tiles
    if (category in (None, "All datasets") or TOPICS[Path(tile[0]).stem][1] == category)
    and term.strip().casefold() in (tile[2] + " " + tile[4]).casefold()
]
st.caption(f"{len(visible):02d} / 15 datasets · Select a field to explore its charts, records, and sources.")
if not visible:
    st.info("No datasets match. Try another search or choose All datasets.")

with st.container(key="collection"):
    for start in range(0, len(visible), 3):
        cols = st.columns(3, gap="small")
        for col, (page, _icon, title, value, sub) in zip(cols, visible[start : start + 3]):
            slug = Path(page).stem
            _, group, number = TOPICS[slug]
            with col.container(key=f"topic_{slug}"):
                st.html(f'''<div class="card-heading"><span>{escape(group)}</span><b>{number}</b></div>
                    <div class="topic-title">{escape(title)}</div>
                    <div class="topic-value">{escape(value)}</div>
                    <p class="topic-caption">{escape(sub)}</p>''')
                st.page_link(page, label=f"Explore {title.lower()} ↗", width="stretch")
