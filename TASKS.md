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
- [ ] **VS-08** — Deploy to Railway from the `Dockerfile`; confirm the warehouse
  bakes in the image build and the app serves on `$PORT`. Record the smoke test.

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
- [ ] **TOPIC-licenses** — Business licenses/registrations (City of Portland). *(next)*
- [ ] **TOPIC-restaurants** — Restaurant inspections (Multnomah County EH) — *only
  if a machine-readable feed exists; else drop + log.*
- [x] **TOPIC-water** — Willamette River (USGS NWIS site 14211720, discharge 00060),
      1972–present. Gage height had no daily series → used discharge.
- [ ] **TOPIC-tourism** — Tourism / Air Travel (Port of Portland PDX passengers +
  Travel Portland). **No gaming.**
- [ ] **TOPIC-art** — Public Art (PortlandMaps) — *optional; verify.*
- [ ] **TOPIC-fire** — Fire Inspections (Portland Fire & Rescue) — *candidate to
  drop; verify (interview: drop if no easy feed).*
- [ ] **TOPIC-marriage** — Marriage Licenses (Multnomah County) — *candidate to
  drop + log (interview: drop if no easy feed).*
- [ ] **TOPIC-extras** — Portland extras chosen in interview: 311, tree canopy,
      bike/transit counts, Urban Growth Boundary. *(verify feeds, then wire)*
- [ ] **TOPIC-overview** — Overview page LAST: headline metrics from the marts that
  actually exist.

---

## Group DEPLOY — Ship & document

- [ ] **DEPLOY-01** — `.gitignore` the build artifacts: `*.duckdb`, `target/`,
  `logs/`, `.venv/`, `.env`, `.DS_Store`, `__pycache__/`.
- [ ] **DEPLOY-02** — Configure `prek` (ruff + ty) pre-commit; `uv run prek
  install`; confirm hooks fire.
- [ ] **DEPLOY-03** — GitHub Actions CI: pytest + ruff + ty on push/PR.
- [ ] **DEPLOY-04** — Full Railway deploy with all kept topics; confirm baked
  warehouse builds and app serves. Note total build time.
- [ ] **DEPLOY-05** — Write `README.md`: what Groening is, the ELT + dbt +
  Streamlit story (Data/DE framing), local run steps, and the source list.
- [ ] **DEPLOY-06** *(optional, interview #7)* — Register in the portfolio
  orchestrator manifest and wire `groening.evanappel.me`.

---

## Suggested sequencing

- **Now:** VS (vertical slice, deployed) → CONFIG/ETL alongside.
- **Then:** re-run interview §7.1, record outcomes, fan out Group TOPIC.
- **Finish:** Overview page, DEPLOY, docs.
