# BLOCKED — what I need from Evan

_Resolved 2026-09-27 (decision review, see `DECISIONS.md`): TOPIC-311 → find a
non-sensitive feed (no campsite data); custom domain → deferred. Neither waits on
you anymore._

- [ ] 🟡 **Confirm the tightened source license strings** — Claude researched each publisher's actual open-data terms (2026-09-27) and tightened the `license` strings in `city_config.SOURCES` (see `DECISIONS.md`). PortlandMaps → PDDL v1.0 (public domain, HIGH confidence) and Metro RLIS → RLIS Open Database License are well-sourced. **Please eyeball the three softer ones before public use:** TriMet GTFS (keyless but no explicit CC/PDDL label — string avoids claiming public domain), OHA marriages, and Multnomah inspections (both "no explicit reuse license found"). If those read fine to you, this is done — check the box.
