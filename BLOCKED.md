# BLOCKED — what I need from Evan

_Resolved 2026-09-27 (decision review, see `DECISIONS.md`): TOPIC-311 → find a
non-sensitive feed (no campsite data); custom domain → deferred. Neither waits on
you anymore._

- [ ] 🟡 **Confirm source license strings (E1 Sources page)** — the `license` field in `city_config.SOURCES` is accurate for federal sources (EPA/NOAA/USGS/BTS = U.S. public domain) but only *descriptive* for the municipal/state ones (City of Portland, Metro, Oregon OHA, Multnomah County). Before the Sources & Methodology page is used publicly, verify each publisher's actual open-data terms and tighten the strings in `city_config.py`. Safe to ship as-is internally; this is accuracy polish, not a correctness bug. _Claude is taking a first pass at researching the terms; Evan to confirm the tightened strings._
