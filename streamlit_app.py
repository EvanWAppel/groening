"""Portland's public data, presented as an editorial field guide."""

import streamlit as st

from ui import TOPICS, apply_style, footer, masthead

st.set_page_config(
    page_title="Groening · A Portland Field Guide",
    page_icon="🌲",
    layout="wide",
)
apply_style()

pages = [st.Page("views/overview.py", title="Overview", default=True)]
pages.extend(st.Page(f"views/{slug}.py", title=info[0]) for slug, info in TOPICS.items())
pages.append(st.Page("views/sources.py", title="Sources & Methodology"))
page = st.navigation(pages, position="hidden")

with st.sidebar:
    st.html('<div class="sidebar-brand">groening<span>.</span></div>'
            '<div class="sidebar-intro">Portland, Oregon<br>An open-data field guide</div>')
    st.page_link("views/overview.py", label="Overview", icon=":material/apps:")
    for category in ("The natural city", "The built city", "Everyday life"):
        st.html(f'<div class="nav-section">{category}</div>')
        for slug, (title, group, _) in TOPICS.items():
            if group == category:
                st.page_link(f"views/{slug}.py", label=title)
    st.html('<div class="nav-section">Reference</div>')
    st.page_link("views/sources.py", label="Sources & Methodology")
    st.html('<div class="sidebar-colophon"><b>One city. Fourteen perspectives.</b><br>'
            'A collection of public records<br>for the endlessly curious.</div>')

masthead()
page.run()
footer()
