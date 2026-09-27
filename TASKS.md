# Groening — TASKS

Implementation task board for [`PRD.md`](./PRD.md). A near-exact port of **Elvis**
(Las Vegas) to the Portland metro. Read [`PRIMER.md`](./PRIMER.md) first for the
Vegas→Portland source mapping and known gotchas.

## How to use this board

- Each task has a unique ID and a `[ ]` checkbox. Mark `[x]` when done, `[~]` when
  partial (leave a note).
- **TDD is mandatory for every parser/transform task**: write a failing `pytest`
  test first, implement until green, then refactor. Shared fixtures go in
  `tests/conftest.py` (DRY).
- **House rules apply** (`CLAUDE.md`): `uv` only (`uv add` / `uv add --dev`, never
  edit `pyproject.toml` by hand), `uv run python`, lint with `ruff`, typecheck with
  `ty`, pre-commits with `prek`. Do not hide or wrap errors — let them surface. Use
  `logging`. Never push to `main`/`master`.
- **Do the vertical slice (Group VS) first and confirm it deploys** before
  fanning out to the rest of the topics.
- **Verify every source before wiring it.** The primer's Portland leads are
  starting points; confirm each is live and machine-readable. `log()` any topic
  you drop for lack of a source.

## Interview outcomes (fill in before coding pages)

Settled on 2026-08-11 (see `PRD.md` §11 Resolved): city = Portland/Multnomah;
stack = identical to Elvis; scope = mirror Elvis where data exists; framing =
broad Data/DE; codename = `groening`.

**Re-run the interview in `PRIMER.md` §7.1 and record answers here before Group
TOPIC:** — done 2026-08-11.

- [x] Metro breadth: **Full tri-county** — Multnomah (051) + Washington (067) +
  Clackamas (005). Use Metro RLIS for regional layers; AQS FIPS list = all three.
- [x] Confirmed drop list: **Drop both Marriage & Fire if no easy feed.** Time-box
  a source check on each; if no clean machine-readable feed, drop and `log()` it.
- [x] Signature water body: **Willamette River (USGS NWIS)** — river stage/flow,
  keyless JSON API.
- [x] Portland-specific extras to add: **311 requests, Tree canopy/trees, Bike/
  transit counts, Urban Growth Boundary** — wire each only if a live feed verifies.
- [x] Deploy target: **Standalone Railway** (from the Dockerfile; no orchestrator).
- [x] Vertical-slice topic: **Building Permits** (PortlandMaps).

## Parallelization guide

```
VS  (vertical slice) ─────────────► must finish & deploy first
        │
        ├── CONFIG (city_config.py)     ─┐
        ├── ETL    (fetch helpers)        │  seeded by VS, refined in parallel
        └── TOPIC  (one page per dataset) ┘  fan out AFTER sources verified
DEPLOY / DOCS: after ≥ VS; finalize at the end.
```

Within Group TOPIC, each dataset is an independent task — assign one agent per
topic. They touch different `stg_`/`mart_`/`views/` files, so they don't collide.

---

## Group VS — Vertical slice (DO FIRST) 🎯

Goal: one topic working end to end — fetch → staging view → mart → Streamlit page
→ **deployed to Railway** — proving the whole pipe before breadth. Pick a
high-confidence source: **Building Permits** or **Parks** (PortlandMaps) or
**Air Quality** (EPA bulk + FIPS swap).

- [x] **VS-01** — Scaffolded the uv project (git init + `uv init`; runtime + dev
  deps added via `uv add`). Imports smoke-test passes.
- [x] **VS-02** — Copied Elvis's `app_db.py`, `dbt_project.yml`, `profiles.yml`,
  `Dockerfile`, `requirements.txt`, `.gitignore`/`.dockerignore`, minimal
  `streamlit_app.py`. Renamed to `portland.duckdb`; dbt name/profile = `groening`.
- [x] **VS-03** — Created `city_config.py` with the VERIFIED permits endpoint
  (`COP_OpenData_PlanningDevelopment/MapServer/89`) + tri-county FIPS, PDX NOAA
  station, Willamette USGS site as recorded constants.
- [x] **VS-04** — Ported fetch helpers into `build_warehouse.py` (`fetch_layer`
  refactored to take a full base URL so config points at FeatureServer *or*
  MapServer). TDD'd `_centroid` + `_epoch_to_date` — 8 tests green.
- [x] **VS-05** — Fetched permits into `raw.building_permits`: 36,263 rows, 29
  cols, WGS84 lon/lat present, dates normalized. Zero-row fetch now raises.
- [x] **VS-06** — `stg_building_permits` view + `sources.yml`; marts
  `mart_permits_monthly`, `mart_permits_by_type`, `mart_permits_map`.
  `dbt build` green (PASS=4).
- [x] **VS-07** — Built `views/building_permits.py` (KPIs + 2 time-series + work-
  class bar + **PyDeck 3D hexbin map** — an upgrade over Elvis's non-spatial
  permits). Verified rendering in-browser. `pytest`/`ruff`/`ty` all green.
- [x] **VS-08** — Deployed to Railway from the `Dockerfile` (GitHub integration,
  project `groening`). Warehouse bakes at build time; app serves on `$PORT` at
  https://groening-production.up.railway.app (HTTP 200, all 13 topics live).
  Restaurant inspections use a committed snapshot fallback because the
  MyHealthDepartment API 403s Railway's datacenter IP.

**Exit criteria:** one page live on Railway; `uv run pytest`, `uv run ruff check .`,
`uv run ty check` all pass locally.

---

## Group CONFIG — City configuration

- [ ] **CONFIG-01** — Verify and record in `city_config.py` the **PortlandMaps**
  (City of Portland) ArcGIS org / services root and the layer paths for the topics
  you keep.
- [ ] **CONFIG-02** — Verify and record the **Metro RLIS** regional GIS root (if
  used for metro-wide layers).
- [ ] **CONFIG-03** — Record **EPA AQS** FIPS: OR state `41`, Multnomah `051` (add
  Washington `067`, Clackamas `005` if metro breadth = full metro).
- [ ] **CONFIG-04** — Record **NOAA GHCN-Daily** station: PDX `USW00024229`.
- [ ] **CONFIG-05** — Record the **Portland Police Bureau** crime data endpoint and
  its format (ArcGIS vs. CSV) + available years.
- [ ] **CONFIG-06** — Record the chosen **signature water body** source (USGS NWIS
  site id for the Willamette gauge, or USACE reservoir feed).

---

## Group ETL — Ingestion hardening

- [ ] **ETL-01** — Confirm the **force-IPv4 for `aqs.epa.gov`** path is carried over
  (see `PRIMER.md` §4). Test that the AQS fetch completes in the target env.
- [ ] **ETL-02** — Confirm the `ssl_verify=False` path exists and is used **only**
  per-host for broken-TLS servers, and logs a warning when engaged.
- [ ] **ETL-03** — Centralize encoding handling (Windows-1252 / cp1252) for muni/
  clerk/health bulk files in `_read_delimited`. TDD with a fixture file.
- [ ] **ETL-04** — Ensure every fetch logs source, URL, and row count; a fetch that
  returns zero rows raises (don't silently ship an empty page).

---

## Group TOPIC — One task per dataset (fan out; TDD each transform)

Start only after the interview outcomes (drop list, metro breadth, water body) are
recorded above and each source is verified. For each: fetch → `stg_` view →
`mart_` table → `views/*.py` page. Drop and **log** any topic without a source.

- [x] **TOPIC-permits** — Building Permits (PortlandMaps MapServer/89). *(VS topic)*
      36,263 geocoded permits; hexbin map + valuation/work-class charts.
- [x] **TOPIC-parks** — Parks (PortlandMaps Environment/35), 316 polygons →
      centroids. No water-feature attribute in Portland → flag dropped + logged.
- [x] **TOPIC-air** — Air Quality (EPA AQS bulk, OR FIPS 41 / tri-county), 2019–2024,
      PM2.5 + Ozone. Sample-Duration filtered; Clackamas Ozone-only (noted). 2020
      wildfire-smoke spike visible.
- [x] **TOPIC-weather** — Rain & Records (NOAA GHCN-Daily PDX), 1938–present. °F/in.
- [x] **TOPIC-crime** — Reported Crime (PortlandMaps ArcGIS Public/Crime 1/40/59),
      rolling 12mo, 51,254 offenses. Hour×weekday heatmap + hexbin map.
- [x] **TOPIC-str** — Short-Term Rentals (PortlandMaps report API), 2,107 permits.
      Web-Mercator → WGS84 reproject (TDD'd).
- [x] **TOPIC-water** — Willamette River (USGS NWIS site 14211720, discharge 00060),
      1972–present. Gage height had no daily series → used discharge.
- [x] **TOPIC-tourism** — Air Travel: BTS international passengers at PDX, monthly
      1990–2025 (Socrata). No gaming. 2020 COVID collapse visible.
- [x] **TOPIC-trees** *(extra)* — Parks Tree Inventory (25,734 pts): species +
      carbon/stormwater benefits. Hexbin map.
- [x] **TOPIC-bike** *(extra)* — PBOT Bicycle Network: miles-built-per-year +
      cumulative growth (segments with a recorded YearBuilt).
- [x] **TOPIC-ugb** *(extra)* — Metro Urban Growth Boundary (~408 sq mi); boundary
      PathLayer map. Single current polygon, no amendment history (logged).
- [x] **TOPIC-marriage** — KEPT (feed exists): Oregon OHA Multnomah aggregate
      county×year counts w/ same-sex breakout, 1995–present.
- [x] **TOPIC-restaurants** — Multnomah County food inspections (MyHealthDepartment
      `searchInspections` JSON POST API). Rolling 6mo, Food program (restaurants +
      carts + warehouses); 0-100 sanitation score, name/address (no coords → no
      map). API hard-caps a query at ~225 rows, so the fetch tiles the window into
      3-day ranges and recursively splits any that overflow. Score-distribution +
      monthly volume/avg-score charts + recent-per-establishment table.
- [~] **TOPIC-licenses** — DROPPED + logged. Portland's is a Revenue tax, not an
      open registry; legacy CivicApps dataset decommissioned.
- [~] **TOPIC-art** — DROPPED + logged. Only a 42-pt unofficial ~2012 downtown
      scrape; RACC publishes no machine-readable geo feed.
- [~] **TOPIC-fire** — DROPPED + logged. Only station/district polygons; no
      inspection or incident feed (matches interview drop-if-no-feed).
- [~] **TOPIC-311** *(extra)* — HELD for Evan. No generic 311 feed; only row-level
      option is illegal-campsite (homelessness) complaints — sensitive; ask first.
- [x] **TOPIC-overview** — Overview landing page (`views/overview.py`, default page).
  Navigational hub: one headline metric per topic pulled from the marts, each tile
  linking to its page. All 13 queries verified against the warehouse; rendered
  in-browser.

---

## Group DEPLOY — Ship & document

- [ ] **DEPLOY-01** — `.gitignore` the build artifacts: `*.duckdb`, `target/`,
  `logs/`, `.venv/`, `.env`, `.DS_Store`, `__pycache__/`.
- [ ] **DEPLOY-02** — Configure `prek` (ruff + ty) pre-commit; `uv run prek
  install`; confirm hooks fire.
- [x] **DEPLOY-03** — GitHub Actions CI (`.github/workflows/ci.yml`): ruff + ty +
  pytest on every push/PR via `uv`. Status badge in the README. Plus dbt
  data-quality tests (`models/marts/schema.yml`): not_null/unique/accepted_values
  on mart grain keys, run by `dbt build` (19 tests, all pass).
- [x] **DEPLOY-04** — Full Railway deploy with all kept topics; baked warehouse
  builds (dbt PASS=42) and the app serves. Build ~13 min end to end (the bulk is
  source fetches plus ~3 min of inspections 403 retries before the snapshot
  fallback; fail-fast on the first 403 would cut that).
- [ ] **DEPLOY-05** — Write `README.md`: what Groening is, the ELT + dbt +
  Streamlit story (Data/DE framing), local run steps, and the source list.
- [ ] **DEPLOY-06** *(optional, interview #7)* — Register in the portfolio
  orchestrator manifest and wire `groening.evanappel.me`.

---

## Phase 2 — portfolio enhancements (backlog)

Sharpens the piece for a Data/DE reviewer. See `PRD.md` §12. v1 (deployed, tested
explorer) is done; these are proposed, not committed. **TDD every parser/transform
as usual.** Log a `DECISIONS.md` entry for each item that carries a real trade-off
(E5 comparison home, E6 package-vs-scaffold) before building it.

### Group PROVE — Make the invisible engineering visible (start here; high signal)

Groups PROVE items are largely independent (different files) — fan out safely.

- [x] **E1 — Sources & Methodology page.** `views/sources.py` (registered in nav +
  sidebar under "Reference"): a methodology blurb + a sortable catalog table
  (dataset, publisher, coverage, **row count from `mart_build_metadata`**, grain/
  transform, terms, source-endpoint link) + a Dropped-topics section. Provenance
  lives in `city_config.SOURCES` (city-specific → the one "which city" file);
  `source_catalog_rows()` joins it to the build-provenance counts and **raises on
  any undocumented raw table** so a new source can't ship without a Sources entry.
  Dropped list moved from `build_warehouse` to `city_config.DROPPED_TOPICS` (so the
  app never imports the build module + its IPv4 socket monkeypatch). TDD'd (8 tests);
  page executes clean in bare mode. **License strings are accurate for federal
  sources (public domain) but descriptive for municipal/state — flagged in
  `BLOCKED.md` to tighten before public use.**
- [x] **E2 — Build-provenance banner.** `build_warehouse.collect_build_metadata`
  (TDD'd, 4 tests) stamps `raw.build_metadata` — one row per loaded raw table
  (name, row_count, shared ISO built_at) — from `_raw_row_counts(con)` after all
  fetches land. dbt: `stg_build_metadata` view + `mart_build_metadata` table
  (per-source grain; unique/not_null tests, all pass). `ui.build_stamp()` renders
  "Data as of \<date\> · N sources · M rows" in the footer (verified: *Sept 26,
  2026 · 13 sources · 222,682 rows*). Grain choice logged in `DECISIONS.md`. Full
  suite 48 passed · ruff · ty clean.
- [x] **E3 — dbt exposures + lineage view.** `models/exposures.yml` declares one
  exposure per Streamlit page (15) with `depends_on` its marts, so lineage is
  source→staging→mart→page-complete (`dbt build` parses all 15). Chose option (b):
  `dbt_artifacts.lineage_edges` / `build_lineage_dot` parse `target/manifest.json`
  into a Graphviz DAG rendered on the Sources page via `st.graphviz_chart`. TDD'd
  (manifest fixture → edges/layers/DOT). Verified against the real manifest: 86
  edges, 14 sources → 15 pages.
- [x] **E4 — In-app data-quality summary.** `dbt_artifacts.summarize_dbt_tests`
  parses `target/run_results.json` into pass/fail counts + a per-type breakdown;
  the Sources page shows "**23 of 23 dbt tests all passing**" with not_null/unique/
  accepted_values metric tiles. TDD'd (5 tests, inline fixtures); verified against
  the real artifact (15 not_null · 7 unique · 1 accepted_values). Both E3/E4 read
  dbt `target/` at runtime — trade-off logged in `DECISIONS.md`; parsers degrade to
  an explicit "run dbt build" note if artifacts are absent.

### Group MULTI — Multi-city template (the differentiator)

- [ ] **E5 — Cross-city comparison.** `ATTACH` (read-only) Portland + Vegas
  (Elvis) + Seattle (Robbins) `.duckdb` files; compare shared marts (weather, air
  quality, permits). **DECISION first:** where it lives (a Groening page vs. a
  standalone "trilogy" app) and how the three artifacts are co-located at
  build/deploy. TDD the cross-city query/normalize helpers.
- [ ] **E6 — Extract the shared engine.** **DECISION first:** full pip-installable
  package (all three repos depend on it, `city_config.py` the only per-city surface)
  vs. the lighter `make new-city` scaffold + "target a new metro" guide. Start with
  the scaffold+guide unless Evan opts into the package. Touches multiple repos —
  own git worktree per repo, merge one at a time (per ROCRLL Orchestrate).

### Group DATA — Portland-specific expansion (breadth)

Each is an independent fetch → `stg_` → `mart_` → `views/*.py`, TDD'd. Verify the
feed is live and machine-readable before wiring; `log()` and drop if not.

- [x] **E7a — TriMet GTFS** (transit). Verified live (GTFS zip, 81 routes / 6,027
  stops). `_parse_gtfs` (TDD'd, 3 tests) pulls routes.txt + stops.txt →
  `raw.transit_routes`/`raw.transit_stops`; staging maps `route_type`→mode and
  filters to boardable stops; 4 marts (summary, by_mode, routes, stops_map) with 8
  data-quality tests. New `views/transit.py` (KPIs · routes-by-mode bar · stops
  hexbin map · route list), wired into nav, Overview (14th tile + count bump),
  `SOURCES` (2 entries → transit page), and a `transit_page` dbt exposure. Full
  dbt build green (34 models, 31 tests); 72 pytest · ruff · ty clean; pages execute
  in bare mode. Skipped trips.txt (67k rows) — a service-frequency view for later.
- [ ] **E7b — 311 / PDX service requests** — pick a **non-sensitive** feed or an
  aggregate (row-level campsite complaints stay HELD; ask Evan before using them).
- [~] **E7c — Tree-canopy change over time.** DROPPED + logged
  (`city_config.DROPPED_TOPICS['tree_canopy']`): Portland's Urban Forestry canopy
  assessment ships as raster/land-cover snapshots, not a tabular canopy-over-time
  feed — no machine-readable time series to chart. The Trees page already covers
  the street-tree inventory.
- [x] **E7d — Housing.** Built **Affordable Housing** from the Portland Housing
  Bureau "Rental Portfolio" (PortlandMaps layer 221, verified live: 380 regulated
  projects, 19,353 regulated units, geocoded). `fetch_housing` (reuses `fetch_layer`)
  → `stg_housing` → 4 marts (summary, by_year, by_type, map) with 5 data-quality
  tests. `views/housing.py` (KPIs · units-completed-per-year · by-type bar ·
  scatter map sized by units), wired into nav, Overview (15th tile + count bump),
  `SOURCES`, and a `housing_page` exposure. Chose the affordable-housing portfolio
  over eviction data (no clean Portland eviction feed) and over demolition permits
  (too permits-adjacent) — logged in `DECISIONS.md`. Full dbt build green (38
  models, 36 tests); 72 pytest · ruff · ty clean; pages execute in bare mode.

### Group SERVE — Serving layer & NL query (ambitious / optional)

- [x] **E8 — Read-only JSON API.** Standalone `api.py` (FastAPI over the same
  `portland.duckdb`, opened `read_only=True`) exposing the 47 marts as JSON:
  `/health`, `/marts` (names + row counts), `/marts/{name}` (rows, `limit`/`offset`
  paged, 1–10000), `/marts/{name}/schema`. Read-only by construction — no
  arbitrary-SQL endpoint, only `main.mart_*` base tables reachable (raw tables and
  `stg_*` views 404), requested names validated against the live catalog before
  touching SQL (mart lookup pinned to `current_database()`, so an ATTACHed second
  catalog can't leak). Rows serialized via native `fetchall()` (pandas-free path,
  keeps int columns int). TDD'd: `tests/test_api.py` (17 tests) runs against a
  throwaway DuckDB via a `get_connection` dependency override; smoke-tested against
  the real warehouse (47 marts, dates/bools intact). Independently reviewed (no
  high-severity findings; medium catalog-pinning + low pandas-fidelity findings
  both adopted). `fastapi`/`uvicorn` added to `pyproject.toml`; deploy left
  single-Streamlit (deploy wiring deferred — logged in `DECISIONS.md`).
- [ ] **E9 — Natural-language query (text-to-SQL).** 🔴 **Gated on the
  personal-key guardrail** — needs a dedicated isolated workspace + a scoped,
  spend-capped key, never Evan's personal Anthropic key (see global `CLAUDE.md`).
  When this task is picked up, add the key checklist to `BLOCKED.md` and do not
  start until it's satisfied and Evan confirms.

---

## Suggested sequencing

- **Now:** VS (vertical slice, deployed) → CONFIG/ETL alongside.
- **Then:** re-run interview §7.1, record outcomes, fan out Group TOPIC.
- **Finish:** Overview page, DEPLOY, docs.
- **Phase 2:** PROVE first (fastest, highest signal) → MULTI (E5 comparison) →
  DATA / SERVE as capacity allows. Log the E5/E6 decisions before building.
