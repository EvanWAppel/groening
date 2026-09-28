"""Shared visual language for the Portland field guide."""

import json
from html import escape
from pathlib import Path

import pydeck as pdk
import streamlit as st

from app_db import query

ASSETS = Path(__file__).parent / "assets"

# Portland metro centering for the neighborhood choropleths.
_PDX_CENTER = {"longitude": -122.66, "latitude": 45.53, "zoom": 9.6}

# One index keeps the navigation and dataset collection in sync.
TOPICS = {
    "building_permits": ("Building Permits", "The built city", "01"),
    "parks": ("Parks", "The natural city", "02"),
    "crime": ("Reported Crime", "Everyday life", "03"),
    "short_term_rentals": ("Short-Term Rentals", "The built city", "04"),
    "restaurant_inspections": ("Restaurant Inspections", "Everyday life", "05"),
    "willamette": ("Willamette River", "The natural city", "06"),
    "weather": ("Rain & Records", "The natural city", "07"),
    "air_quality": ("Air Quality", "The natural city", "08"),
    "trees": ("Trees", "The natural city", "09"),
    "bike": ("Bike Network", "The built city", "10"),
    "tourism": ("Air Travel", "Everyday life", "11"),
    "marriage": ("Marriages", "Everyday life", "12"),
    "ugb": ("Urban Growth Boundary", "The built city", "13"),
    "transit": ("Transit", "The built city", "14"),
    "housing": ("Affordable Housing", "The built city", "15"),
    "heritage_trees": ("Heritage Trees", "The natural city", "16"),
    "historic": ("Historic Resources", "The built city", "17"),
    "service_requests": ("Service Requests", "Everyday life", "18"),
}


def apply_style() -> None:
    st.html(ASSETS / "style.css")


def masthead() -> None:
    st.html('''<div class="masthead"><span>GROENING <b>／</b> A PORTLAND FIELD GUIDE</span>
        <span class="masthead-location">45.52° N &nbsp; 122.68° W <i>↗</i></span></div>''')


def page_header(topic: str) -> None:
    title, category, number = TOPICS[topic]
    st.page_link("views/overview.py", label="← All datasets")
    st.html(f'<div class="eyebrow detail-eyebrow">{escape(category)} <span>／ {number}</span></div>')
    st.title(title)


def build_stamp() -> str:
    """"Data as of <date> · N sources · M rows", read from the provenance mart.

    The warehouse is baked at build time, so this is exactly how fresh the data
    is. Reads mart_build_metadata, which build_warehouse.py stamps every build.
    """
    row = query(
        "select max(built_at) as built_at, count(*) as sources, "
        "sum(row_count) as rows from main.mart_build_metadata"
    ).iloc[0]
    built = row["built_at"].strftime("%B %-d, %Y")
    return f"Data as of {built} · {int(row['sources'])} sources · {int(row['rows']):,} rows"


def neighborhood_choropleth(df, value_label: str, accent: tuple[int, int, int]) -> None:
    """Render a Portland neighborhood choropleth from a marts frame.

    ``df`` has one row per neighborhood polygon with ``neighborhood``,
    ``boundary_json`` (a WGS84 coordinate ring), and ``n`` (the count to shade by).
    Fill interpolates from a near-white base to ``accent`` on a sqrt scale, so a
    single dense neighborhood (e.g. downtown) doesn't wash the rest to white.
    """
    counts = df["n"].astype(float)
    peak = max(counts.max(), 1.0)
    base = (247, 244, 239)  # warm paper, matching the field-guide palette
    ar, ag, ab = accent

    records = []
    for row in df.itertuples(index=False):
        t = (max(row.n, 0) / peak) ** 0.5  # sqrt compresses the long tail
        fill = [
            round(base[0] + (ar - base[0]) * t),
            round(base[1] + (ag - base[1]) * t),
            round(base[2] + (ab - base[2]) * t),
            220,
        ]
        records.append(
            {
                "polygon": json.loads(row.boundary_json),
                "neighborhood": row.neighborhood,
                "n": int(row.n),
                "fill": fill,
            }
        )

    layer = pdk.Layer(
        "PolygonLayer",
        data=records,
        get_polygon="polygon",
        get_fill_color="fill",
        get_line_color=[255, 255, 255],
        line_width_min_pixels=0.5,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
    )
    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(pitch=0, **_PDX_CENTER),
            tooltip={"text": "{neighborhood}\n{n} " + value_label},
        )
    )


def footer() -> None:
    st.html(f'''<footer class="site-footer">
        <div><span class="footer-brand">groening.</span><p>A closer look at the place we call Portland.</p></div>
        <div><span class="eyebrow">OPEN DATA. OPEN CURIOSITY.</span>
        <p>Public records, thoughtfully explored. Coverage varies by dataset.</p>
        <p class="footer-provenance">{escape(build_stamp())}</p>
        <p>By <a href="https://evanappel.me/projects" target="_blank" rel="noopener noreferrer">Evan Appel ↗</a>
        &nbsp;·&nbsp; <a href="https://github.com/EvanWAppel/groening" target="_blank" rel="noopener noreferrer">View the source ↗</a></p></div>
        </footer>''')
