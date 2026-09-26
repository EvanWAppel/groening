# BLOCKED — what I need from Evan

- [ ] 🟡 **TOPIC-311 sensitive-data decision** — the only row-level option is illegal-campsite (homelessness) complaints, which is sensitive. Approve inclusion before it's wired, or say to leave it out. Explicitly held for you.
- [ ] 🟡 **Custom domain (DEPLOY-06)** — register in the portfolio orchestrator manifest and wire `groening.evanappel.me`. Your call on priority.
- [ ] 🟡 **Confirm source license strings (E1 Sources page)** — the `license` field in `city_config.SOURCES` is accurate for federal sources (EPA/NOAA/USGS/BTS = U.S. public domain) but only *descriptive* for the municipal/state ones (City of Portland, Metro, Oregon OHA, Multnomah County). Before the Sources & Methodology page is used publicly, verify each publisher's actual open-data terms and tighten the strings in `city_config.py`. Safe to ship as-is internally; this is accuracy polish, not a correctness bug.
