# DECISIONS — the Ledger

The durable *why*. One entry per decision with a **real trade-off** — what was chosen, what was rejected, and why. Append-only; newest at the bottom. The agent drafts the entry; the human confirms it.

---

## 2026-09-26 — E2 build-provenance mart grain: per-source, not pre-aggregated

**Chose:** `mart_build_metadata` at **one-row-per-source grain** (table_name, row_count, built_at), and let the "Data as of <date> · N sources · M rows" banner aggregate it in the query (`max(built_at)`, `count(*)`, `sum(row_count)`).

**Rejected:** a pre-aggregated single-row summary mart (built_at, source_count, total_rows) — the minimal shape the banner alone needs.

**Why:** the per-source grain is a strict superset. It powers the E2 banner today via a trivial aggregate and is exactly what the E1 Sources & Methodology page needs (per-dataset row counts), so E1 reuses this mart instead of adding a second one. It also carries a real `unique(table_name)` data-quality test (a single-row summary can't). Cost: the banner does a one-row aggregate on each load instead of reading a literal — negligible against a 13-row table.

---

## 2026-09-26 — E3/E4 read dbt `target/` artifacts at runtime, not baked into the warehouse

**Chose:** the Sources page reads `target/manifest.json` (lineage, E3) and `target/run_results.json` (test summary, E4) directly at runtime, via pure parsers in `dbt_artifacts.py`.

**Rejected:** a post-`dbt build` step that loads those artifacts into tables inside `portland.duckdb`, so the app reads only the warehouse (as it does for all topic data).

**Why:** the Dockerfile runs `dbt build` *inside* the image, which regenerates `target/` after the source COPY — so both JSON files are guaranteed present at runtime even though `target/` is `.dockerignore`d. Reading them directly needs no Dockerfile change and no second dbt pass (the warehouse is already sealed when `run_results.json` is written, so it can't be modeled by dbt afterward without re-running). Cost: the app now depends on dbt's artifact layout and on `target/` surviving into the runtime image; both parsers return `None` and the page shows an explicit "run dbt build" note if the files are absent, so a missing artifact degrades visibly rather than crashing. Revisit if the deploy ever stops shipping `target/`.

---

## 2026-09-26 — E7d "Affordable Housing" dataset: Housing Bureau portfolio, not eviction or demolitions

**Chose:** the Portland Housing Bureau "Rental Portfolio" (PortlandMaps layer 221) — 380 financed/regulated affordable-housing projects with unit counts, building type, and geometry — as the E7d "housing" topic.

**Rejected:** (a) eviction data — no clean, current, machine-readable Portland/Multnomah eviction feed found; (b) Residential Demolition Permits (layer 126, ~6,530 rows) — verified live and richer, but structurally a near-duplicate of the existing Building Permits page (issue date, valuation, units, neighborhood, hexbin), so it adds volume more than a new perspective.

**Why:** the affordable-housing portfolio is a genuinely distinct lens — regulated vs. total units, affordability, where subsidized housing sits — that no existing page covers, which is the point of E7 (add perspectives Vegas lacked). Demolitions remains a good future "built vs. torn down" companion to permits if breadth is wanted later. Tree-canopy (E7c) was dropped in the same pass: Portland publishes canopy as rasters, not a tabular time series (logged in `city_config.DROPPED_TOPICS`).

---

## 2026-09-26 — E8 JSON serving layer ships as a standalone module, not wired into the deploy

**Chose:** build the read-only JSON API as a standalone `api.py` (FastAPI over the same `portland.duckdb`, opened `read_only=True`), TDD'd via `tests/test_api.py` with a `get_connection` dependency override onto a throwaway DuckDB. Endpoints: `/health`, `/marts` (names + row counts), `/marts/{name}` (rows, `limit`/`offset` paged), `/marts/{name}/schema`. The Dockerfile/Railway deploy is left untouched — it still serves only Streamlit on `$PORT`.

**Rejected:** wiring the API into the live deploy now — either a second Railway service or a process manager running Streamlit + uvicorn behind one port.

**Why:** E8 is the "ambitious/optional" SERVE group; its value is demonstrating a data *product* (the marts as JSON), which the module + tests already deliver. Adding process supervision or a reverse proxy to a currently-single-process image is real deploy risk (port routing, SIGTERM handling, health checks) for no user-facing gain yet, so it's deferred as its own decision. Design guarantees keep it safe to expose later: read-only connection, no arbitrary-SQL endpoint, and only `main.mart_*` base tables reachable (raw tables and staging views 404), with requested names validated against the live catalog before ever touching SQL. `fastapi`/`uvicorn` are in `pyproject.toml` but deliberately NOT in `requirements.txt`, since the Docker image doesn't run the API — adding them there would ship unused runtime deps.

**Review hardening (adopted from the independent adversarial review):** (1) mart discovery is pinned to `current_database()`, not just the `main` schema, so if a second catalog is ever `ATTACH`ed its own `main.mart_*` tables can't leak into the API. (2) rows are serialized via DuckDB's native `fetchall()` + FastAPI's encoder instead of a pandas `to_json` roundtrip — this keeps a nullable-int column an int (pandas coerces it to float, e.g. `2024` → `2024.0`) and makes the endpoint pandas-free. Both were medium/low advisory findings; no high-severity issue was raised.

---

## 2026-09-27 — Density maps: neighborhood choropleths, point-in-polygon tagged in pure Python

**Chose:** replace the four extruded 3D hexbin ("hex tower") maps (crime, building permits, historic resources, trees) with flat **neighborhood choropleths** shaded by per-neighborhood count, and flatten the transit map to a 2D stop scatter (no towers). The areal unit is PortlandMaps "Neighborhood Boundaries" (COP Open Data Boundary layer 3, 125 polygons), added once as a shared support layer (`raw.neighborhoods` → `stg_neighborhoods`). Each geocoded point is tagged with its containing neighborhood at **build time via a pure-Python ray-casting point-in-polygon** (`_point_in_ring` + `assign_neighborhood`/`tag_neighborhoods`, bbox-prefiltered), adding a `hood_name` column to the four raw point tables; the `*_choropleth` marts are then a plain `GROUP BY hood_name` left-joined to the boundary polygons.

**Rejected:** (a) **DuckDB `spatial` extension** doing the point-in-polygon in SQL inside dbt — idiomatic and keeps the join in the mart layer, but adds a build-time `INSTALL spatial` extension download (network dependency the project's gotchas explicitly warn against) and can't be unit-tested with pytest the way a pure helper can. (b) **Joining permits/historic on their existing `NBRHOOD`/`NEIGHBORHOOD` name field** instead of a spatial join — avoids geometry but is fragile (name spellings/abbreviations must match the boundary layer exactly) and would make two topics behave differently from crime/trees. A uniform spatial tag guarantees every topic's counts align to the same 125 polygons.

**Why:** the choropleth reads as "where in the city" far better than extruded towers, and pure-Python PIP matches the codebase's existing TDD'd geometry helpers (`_centroid`, `_webmerc_to_wgs84`) with zero new runtime/build dependency and full unit-test coverage (`tests/test_neighborhoods.py`). A neighborhood name can span several multipart polygons, so `neighborhood` is intentionally **not unique** in the choropleth marts (each polygon of a name is shaded with that name's total); views dedupe by name for any headline stat. The four now-unused point-map marts (`mart_{crime,permits,historic,trees}_map`) were deleted and their page exposures repointed to the `*_choropleth` marts, so lineage stays honest. Transit stayed a point layer (flattened) because a route/stop network reads better as points than shaded regions.

---

## 2026-09-27 — Phase 2 direction: defer E5, scaffold-not-package for E6, non-sensitive 311, defer custom domain

Four Phase 2 direction calls made by Evan in a decision review (agent-drafted, Evan-confirmed):

**E5 — Cross-city comparison: DEFERRED.** Chose not to build the Portland+Vegas+Seattle comparison now. Rejected both the in-Groening comparison page and the standalone "trilogy" app. **Why:** both require co-locating three warehouse artifacts at build/deploy time (real plumbing) for a feature that's the "differentiator" but not core to Groening as a standalone piece; effort is better spent on breadth/polish. Revisit if the trilogy story becomes the headline.

**E6 — Shared engine: SCAFFOLD + GUIDE, not a package.** Chose the lighter `make new-city` scaffold plus a "target a new metro" guide, with `city_config.py` as the per-city surface. Rejected the pip-installable package that all three repos depend on. **Why:** a shared package creates a cross-repo versioning/upgrade surface across Elvis/Groening/Robbins for three apps that already work as independent ports; the scaffold delivers most of the "new cities are cheap" value without that maintenance burden. This was already the TASKS.md default.

**TOPIC-311 / E7b — Find a NON-SENSITIVE feed.** Chose to hunt for a non-sensitive or aggregate 311 / service-request feed and wire that; drop-and-log if nothing clean exists. Rejected wiring the row-level illegal-campsite (homelessness) complaints — the only row-level option — on sensitivity grounds. **Why:** the app is a public open-data explorer; row-level homelessness complaint data is sensitive and not worth the ethical/optics cost when an aggregate alternative may exist. This clears the long-standing TOPIC-311 "HELD for Evan" blocker.

**DEPLOY-06 — Custom domain: DEFERRED.** Keep the Railway `*.up.railway.app` URL for now; don't wire `groening.evanappel.me` yet. **Why:** cosmetic; no functional gain. Revisit alongside the broader portfolio-orchestrator manifest work.

---

## 2026-09-27 — Source license strings verified against publishers' actual terms (confirmed by Evan, blocker triage 2026-10-23)

**Chose:** replace the descriptive municipal/state `license` strings in
`city_config.SOURCES` with strings that cite each publisher's actual open-data
terms (researched 2026-09-27; DRY'd into `_LICENSE_*` constants).

- **City of Portland / PortlandMaps (9 datasets)** → **Open Data Commons PDDL v1.0
  (public domain)**, per the City's Open Data ToS §VI (rev. 2022-07-05,
  https://www.portlandmaps.com/bps/arpa/tos.pdf). HIGH confidence — the ToS is
  explicit. `crime` gets a variant naming the Public/Crime service (it's not on the
  `/od/` portal path, though the same City ToS governs it).
- **Metro RLIS (`ugb`)** → **RLIS Open Database License (ODbL-style), attribution +
  share-alike**, confirmed in the UGB layer's own metadata ("Use Constraints: …
  RLIS Open Database End User License Agreement"). HIGH that it's the open license;
  MEDIUM on the bare "ODbL" label, so the string says "ODbL-style" + the URL.
  _2026-10-23:_ the UGB source moved to the official `OregonMetro.RLIS` ArcGIS Online
  layer (`services2.arcgis.com/McQ0OlIABe29rJJy/.../Urban_Growth_Boundary_UGB`,
  item `e3a9453a1ce547a7b2ee4baac037540e`) after the old Metro DRC layer was retired.
  Its item `licenseInfo` names the same RLIS Open Database EULA, so the license
  string is unchanged.

**Softer strings (flagged for Evan):**
- **TriMet GTFS** — the static feed is keyless/openly published, but TriMet stamps
  no CC/PDDL label and its site ToS reads restrictively. String says "publicly
  published, keyless; TriMet developer Terms of Use" — deliberately NOT "public
  domain"/"CC BY" without a citation. MEDIUM confidence.
- **OHA marriages** / **Multnomah inspections** — both are public
  aggregate/records publications with **no explicit reuse license** found. Strings
  say exactly that, and clarify OHA = the aggregate publication (record-level OHA
  vital data is confidential under ORS 432.350; not what we fetch).

**Why:** the Sources & Methodology page is public-facing; accurate license
provenance is part of the data-product story. Federal sources were already correct
(U.S. public domain) and were left untouched.

**Confirmed:** Evan approved this agent-drafted entry, including the three softer
strings (TriMet GTFS, OHA marriages, Multnomah inspections), as written — Evan,
blocker triage 2026-10-23.

---

## 2026-09-27 — Catalog the neighborhoods support layer in SOURCES (Sources-page fix)

**Bug:** PR #8 added `raw.neighborhoods` (the choropleth base layer) without a
`city_config.SOURCES` entry. A full build stamps every raw table into
`mart_build_metadata`, and `source_catalog_rows` deliberately raises on any
uncatalogued table, so the Sources & Methodology page would raise a KeyError on
every build since #8.

**Chose:** add a "Neighborhood Boundaries" SOURCES entry (Evan's call), plus a
regression test that parses `build_warehouse.main()`'s `load_raw` calls and
asserts each loaded table is catalogued. **Rejected:** a `SUPPORT_TABLES`
exclusion set — it would hide a real upstream dependency of five choropleth
pages from the provenance page, which is the opposite of what that page is for.

---

## 2026-09-27 — E7b Service Requests: graffiti + potholes, unified into one raw table

**Chose:** build E7b from the two non-sensitive, row-level request layers Portland
publishes on PortlandMaps (Public folder): **BPS Graffiti Reports**
(`BPS_Graffiti/MapServer/1`, ~49k rows, Sept 2022 – present) and **PBOT Pothole
Repair Reports** (`PBOT_Maintenance/MapServer/0`, rolling 12 months, ~6k rows),
shown together on one "Service Requests" page (Evan picked "both on one page").
They land as a **single `raw.service_requests` table** keyed by `request_type`,
unified at build time by a TDD'd pure helper (`unify_service_requests`), with
status normalized to Open/Closed (raw status kept) and an **unmapped status
raising** rather than being guessed.

**Rejected:** (a) **IRP campsite reports** (`OMF_IRP_Layers`, `IRP Campsite
Reports`) — ruled out on sensitivity grounds (2026-09-27 direction decision).
(b) **BES Odor Complaints** — carries property-owner names/addresses (PII) on
every row. (c) **BDS Noise Complaints** — only ~400 rows/yr, too thin for a page.
(d) **One raw table per request type** — mirrors the source layers, but every
mart would need a UNION and a third request type would mean new models; the
unified table makes each mart a `GROUP BY request_type` and a new layer just
another stack in `unify_service_requests`.

**Why:** Portland has no generic 311 feed, so "311-style" is the honest framing
(the page says so). The two layers have different coverage windows (graffiti ~4
years vs potholes rolling 12 months), so the page labels each window explicitly
rather than implying a like-for-like comparison.

## 2026-10-05 — Add the Ask Tiresias page (drafted by Claude, awaiting Evan's confirmation)

Groening adopts the Tiresias library (github.com/EvanWAppel/tiresias v0.1.0, pinned
by the tag's commit archive) with its own `tiresias.yml`. Scope: 50 of 51 marts;
**`mart_build_metadata` excluded** (pipeline bookkeeping). Map-only: the six
`boundary_json` polygon columns and `mart_transit_routes.route_color`. Planner
notes carry the count traps (choropleth rows repeat a neighborhood's `n` per
polygon; rolling windows for crime, inspections, potholes; daily-mean precip;
partial latest tourism year; bad-air days double-count across pollutants).
Grounding threshold **0.62**, midway between the generic off-topic band and the
lowest answerable question (rejected: 0.66+, which would refuse the subtle cases
too but within ~0.03 of a real question). All 198 column docs written from code;
14 unsure claims in `TIRESIAS.md`. `requires-python` narrowed to 3.12. Two
mixed-case columns read as undocumented until Tiresias v0.1.1 (engine fix, PR #5).

## 2026-10-22 — Custom domain is live; point the docs at it

Supersedes DEPLOY-06's "deferred". `groening.evanappel.me` now serves the app (HTTP 200
on `/` and page paths, checked 2026-10-22), so `README.md`, `models/exposures.yml` and
`project.toml` use it as the canonical URL. The Railway origin
`groening-production.up.railway.app` still serves; closing it is a separate
`_system` task (`origin_urls_closed = false`). Rejected: keeping the Railway URL in the
docs, which would advertise an address slated to close.

## 2026-10-24 — E6 scaffold copies the engine verbatim at stamp time (drafted by Claude, awaiting Evan's confirmation)

**Chose:** `new_city.py` (behind `make new-city`) lifts the city-agnostic helpers
(`fetch_layer`, `fetch_features`, `_centroid`, `_epoch_to_date`, `_urlopen`,
`_ssl_ctx`, `_get_json`, IPv4-first, `load_raw`, build provenance) **out of
Groening's own `build_warehouse.py` by name (AST source segments) at generation
time**, and wraps them in a stub with an empty `FETCHERS` registry. A test asserts
the stamped copies are byte-identical to Groening's. The rest of the skeleton
(`city_config.py` stub, dbt project, one-page app, Dockerfile, catalog-contract
test) comes from `scaffold/*.tmpl`. The stamped project is runnable: its own tests
pass, and with one fake fetcher it builds the warehouse and passes `dbt build`.

**Rejected:** (a) hand-maintained template copies of the helpers, which drift
silently from the reference implementation; (b) copying all of Groening's
`build_warehouse.py`, which drags in 18 Portland fetchers that won't import
against a stub config; (c) refactoring the helpers into a shared module first,
which would be a redesign ("architecture is identical to Elvis") and the start of
the rejected package.

**Trade-off:** a stamped project gets a *snapshot*. Engine fixes made in Groening
afterwards don't reach it, which is the cost the 2026-09-27 scaffold-over-package
call accepted. Also: the generated `pyproject.toml` has empty dependencies (added
with `uv add`, per house rules) and the stamped app leaves out Tiresias / the
FastAPI layer, so it needs no key.

---

## 2026-10-23 — E7b follow-ups: Portland wall-clock timestamps; unmapped graffiti status fails the build

Evan's calls on TASKS E7b-followups (1) and (2), taking the recommended option for
each (agent-drafted, confirmed by Evan, blocker triage 2026-10-23).

**(1) Chose:** convert ArcGIS dates to `America/Los_Angeles` once, in `fetch_layer`
(zone in `city_config.LOCAL_TZ`), so every staging model that reads
`YYYY-MM-DD HH:MM:SS` as local time is right. The "not in the future" filters in
`stg_service_requests` and `stg_crime` compare against Portland's wall clock
(`timezone('America/Los_Angeles', now())`), so the cutoff no longer depends on the
build machine's zone. **Rejected:** keeping naive UTC and labelling it on the
pages, which leaves evening reports in the wrong day/month bucket. **Trade-off:**
every `fetch_layer` date column shifts 7–8 h earlier, so crime, permits and service
request day/month counts move slightly at the edges on the next build. The
scaffold's stub config gets `LOCAL_TZ = "UTC"` to be set per city.

**(2) Chose:** an unmapped graffiti `Graffiti_Status` raises in
`stg_service_requests` (`error('Unmapped graffiti status: …')`), matching the
`unify_service_requests` rule for request status. **Rejected:** keeping a silent
`'Other'` bucket with a log line. **Trade-off:** a new status value from BPS now
fails `dbt build` (and so the deploy) until a bucket is added; that is the point,
since a growing catch-all hides data drift. The `%referred%`-before-`open%` order was
left as is; it was not part of this call.

