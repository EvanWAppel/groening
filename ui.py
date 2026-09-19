"""Shared visual language for the Portland field guide."""

from html import escape
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).parent / "assets"

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


def footer() -> None:
    st.html('''<footer class="site-footer">
        <div><span class="footer-brand">groening.</span><p>A closer look at the place we call Portland.</p></div>
        <div><span class="eyebrow">OPEN DATA. OPEN CURIOSITY.</span>
        <p>Public records, thoughtfully explored. Coverage varies by dataset.</p>
        <p>By <a href="https://evanappel.me/projects" target="_blank" rel="noopener noreferrer">Evan Appel ↗</a>
        &nbsp;·&nbsp; <a href="https://github.com/EvanWAppel/groening" target="_blank" rel="noopener noreferrer">View the source ↗</a></p></div>
        </footer>''')
