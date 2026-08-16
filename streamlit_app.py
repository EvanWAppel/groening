"""Portland-Metro Open-Data Explorer — the interactive demo behind the portfolio.

Raw Portland / Multnomah-metro open data is loaded into DuckDB, modeled with dbt,
and served here. This entry point just wires up the multi-page navigation; each
page lives in ``views/`` and queries the dbt marts via ``app_db.query``.

Pages are added as their topic vertical (fetch -> staging -> mart -> page) lands.
The vertical slice ships Building Permits first.
"""

import streamlit as st

st.set_page_config(
    page_title="Portland Open-Data Explorer",
    page_icon="🌲",
    layout="wide",
)

pages = [
    st.Page("views/overview.py", title="Overview", icon="🌲", default=True),
    st.Page("views/building_permits.py", title="Building Permits", icon="🏗️"),
    st.Page("views/parks.py", title="Parks", icon="🌳"),
    st.Page("views/crime.py", title="Reported Crime", icon="🚨"),
    st.Page("views/short_term_rentals.py", title="Short-Term Rentals", icon="🏠"),
    st.Page("views/restaurant_inspections.py", title="Restaurant Inspections", icon="🍽️"),
    st.Page("views/willamette.py", title="Willamette River", icon="🌊"),
    st.Page("views/weather.py", title="Rain & Records", icon="🌧️"),
    st.Page("views/air_quality.py", title="Air Quality", icon="💨"),
    st.Page("views/trees.py", title="Trees", icon="🌲"),
    st.Page("views/bike.py", title="Bike Network", icon="🚲"),
    st.Page("views/tourism.py", title="Air Travel", icon="✈️"),
    st.Page("views/marriage.py", title="Marriages", icon="💍"),
    st.Page("views/ugb.py", title="Urban Growth Boundary", icon="🗺️"),
]

st.navigation(pages).run()
