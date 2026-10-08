# BLOCKED — what I need from Evan

_Resolved 2026-09-27 (decision review, see `DECISIONS.md`): TOPIC-311 → find a
non-sensitive feed (no campsite data); custom domain → deferred. Neither waits on
you anymore._

- [ ] 🟡 **Confirm the tightened source license strings** — Claude researched each publisher's actual open-data terms (2026-09-27) and tightened the `license` strings in `city_config.SOURCES` (see `DECISIONS.md`). PortlandMaps → PDDL v1.0 (public domain, HIGH confidence) and Metro RLIS → RLIS Open Database License are well-sourced. **Please eyeball the three softer ones before public use:** TriMet GTFS (keyless but no explicit CC/PDDL label — string avoids claiming public domain), OHA marriages, and Multnomah inspections (both "no explicit reuse license found"). If those read fine to you, this is done — check the box.

- [ ] 🔴 **Dedicated, spend-capped Anthropic key for groening's Ask Tiresias page** — in the Anthropic Console create a separate workspace (e.g. `tiresias-groening`), set a monthly spend limit + alert (Elvis uses $10), mint a key there, and put it in `groening/.env` as `ANTHROPIC_API_KEY=…` (local live eval) and in Railway → groening → Variables (the page). Then tell Claude it is not your personal/default key. Until then the page shows a "needs a key" notice and the live gold eval can't run.
- [ ] 🟡 **Review the Tiresias gold set and column-doc claims** — skim `evals/tiresias_gold.yaml` (25 drafted questions: are the "answer" ones answerable and the "abstain" ones not?) and check the 14 claims in `TIRESIAS.md` → "Column-doc claims to check against the data". Edit `models/marts/schema.yml` directly or note corrections for Claude.
- [ ] 🔴 **Approve merging the `tiresias` PR** (merge = deploy on Railway). Safe before the key exists: without it the page only shows a notice.

