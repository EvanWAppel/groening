# BLOCKED — what I need from Evan

_Resolved 2026-09-27 (decision review, see `DECISIONS.md`): TOPIC-311 → find a
non-sensitive feed (no campsite data); custom domain → deferred. Neither waits on
you anymore._

_Resolved 2026-10-23 (blocker triage): license strings confirmed; dedicated
`groening` Anthropic workspace key ($10/month cap, $5 alert) set on Railway and
confirmed not personal; E7b follow-ups decided (Portland time, raise on unmapped
graffiti status), see `DECISIONS.md`._

- [ ] 🟡 **Review the Tiresias gold set and column-doc claims** — skim `evals/tiresias_gold.yaml` (25 drafted questions: are the "answer" ones answerable and the "abstain" ones not?) and check the 14 claims in `TIRESIAS.md` → "Column-doc claims to check against the data". Edit `models/marts/schema.yml` directly or note corrections for Claude.
- [x] 🔴 **Approve merging the `tiresias` PR** (merged as PR #15 on 2026-10-08) (merge = deploy on Railway). Safe before the key exists: without it the page only shows a notice.
- [ ] 🟡 **Pick which topics fall back to a last-good snapshot when their source dies** — Evan chose option (c) on 2026-10-24 (recorded in `DECISIONS.md`, 2026-10-24 entry): instead of one dead source (like the retired UGB layer on ~2026-10-18) failing every deploy, a listed topic loads its last good snapshot from `data/`, the same way `restaurant_inspections` already does. What's still missing is the list. Candidates, the raw tables `build_warehouse.py` fetches: `ugb` (Metro RLIS, the one that broke), `building_permits`, `parks`, `housing`, `historic`, `trees`, `heritage_trees`, `bike_network`, `crime`, `service_requests`, `short_term_rentals` (PortlandMaps), `weather` (NOAA), `willamette` (USGS), `air_quality` (EPA AQS), `marriage` (Oregon OHA), `tourism` (BTS), and the TriMet GTFS set `transit_routes`/`transit_stops`/`transit_trips`/`transit_calendar`. `restaurant_inspections` already has a snapshot. `neighborhoods` is the polygon layer every point topic is tagged with, so it's a poor candidate unless its snapshot is kept too. To unblock: reply in chat with the topic names (or "all except X"), or list them under the `DECISIONS.md` entry. Claude then implements it test-first.
