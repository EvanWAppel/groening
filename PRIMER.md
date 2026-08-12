# Groening — Handoff Primer

> **Purpose:** Everything a fresh repo (and a fresh Claude session) needs to build
> a Portland-metro clone of **Elvis**, Evan's Las Vegas open-data explorer.
> **Owner:** Evan Appel · **Date:** 2026-08-11 · **Status:** Handoff v1
>
> Read this first, then work from [`PRD.md`](./PRD.md) and [`TASKS.md`](./TASKS.md).
> House rules live in [`CLAUDE.md`](./CLAUDE.md) and are non-negotiable.

---

## 0. TL;DR

Build **Groening**: an interactive, multi-page **Streamlit** app that ingests
free public datasets about the **Portland, OR metro** (Multnomah County core;
extend to Washington + Clackamas where easy) and presents them as maps, charts,
and searchable tables. It is a near-exact port of **Elvis** (Las Vegas). Same
architecture, same toolchain, same deploy target — **only the data sources and
city-specific configuration change.**

- **ELT:** `build_warehouse.py` fetches public data → raw tables in a DuckDB file →
  **dbt-duckdb** models it into `staging/` views and `marts/` tables.
- **App:** `streamlit_app.py` routes to `views/*.py` pages that query the marts
  through a cached `app_db.query()` helper.
- **Deploy:** a `Dockerfile` **bakes the warehouse at build time** (`build_warehouse.py`
  then `dbt build`), then runs Streamlit. Ships to **Railway**.
- **Codename:** `groening` (Matt Groening — the Portland-born creator of *The
  Simpsons*; a recognizable Portland figure, analog to "Elvis" being a recognizable
  Vegas figure). Bikeable; rename freely.

The codename decision, the identical-stack decision, the mirror-Elvis scope, and
the broad Data/DE framing all came out of the interview in **§7** — that's the
unified understanding this document encodes.

---

## 1. The reference: what Elvis is

Elvis (`portfolio/elvis`) is a Streamlit app over a baked DuckDB warehouse. Its
shape is the blueprint you are copying:

```
elvis/
├── build_warehouse.py     # ETL orchestrator — fetches every source into raw.* DuckDB tables
├── streamlit_app.py       # multi-page router (st.Page + st.navigation)
├── app_db.py              # shared read-only DuckDB connection + @st.cache_data query()
├── dbt_project.yml        # dbt: staging=view, marts=table
├── profiles.yml           # dbt-duckdb profile, path -> vegas.duckdb
├── Dockerfile             # build: build_warehouse.py && dbt build ; run: streamlit
├── requirements.txt       # pip fallback used inside Docker
├── pyproject.toml / uv.lock
├── models/
│   ├── staging/           # ~15 stg_*.sql (raw -> light normalize) + sources.yml
│   └── marts/             # ~12 mart_*.sql (aggregations / viz-ready wide tables)
├── views/                 # 14 *.py Streamlit pages, one per topic
└── vegas.duckdb           # ~220 MB; NOT in git; rebuilt every deploy
```

**Data flow:** `build_warehouse.py` (build time) → `raw.*` tables → `dbt build`
→ `staging` views → `marts` tables → Streamlit reads marts at runtime.

**Elvis's 14 pages (the topic menu to mirror):** Overview, Public Art,
Restaurant Inspections, Fire Inspections, Metro (Police) Calls, Building Permits,
Business Licenses, Short-Term Rentals, Parks, Marriage Licenses, Tourism & Gaming,
Lake Mead (reservoir level), Desert Heat (weather extremes), Air Quality.

**Key fetch helpers in `build_warehouse.py` you will reuse almost verbatim:**

- `fetch_layer(service, org, layer, geometry, out_sr=4326)` — generic ArcGIS
  FeatureServer pagination.
- `fetch_features(base_url, where="1=1", geometry, out_sr=4326, ssl_verify=True)`
  — flexible ArcGIS fetch; `ssl_verify=False` handles servers with broken TLS
  (Vegas needed it for Clark County's `gisgate`).
- `_centroid(geom)` — (lon, lat) from a point or polygon ring.
- `_epoch_to_date(ms)` — ArcGIS epoch-millis → ISO date.
- `_urlopen()` / `_read_delimited()` — HTTP + delimited-file parsing (health-dept
  bundles, marriage CSVs) with encoding handling (Windows-1252 / cp1252).

**No secrets.** Everything is public data. City-specific config is hardcoded as
constants near the top of `build_warehouse.py`. For Groening, **lift those
constants into a `city_config.py` module** so the swap is a single file (see §5).

---

## 2. What stays identical (do not re-litigate)

Per the interview, the stack is **identical**. Copy these wholesale:

- **DuckDB** single-file warehouse; **dbt-duckdb** with `staging`=views, `marts`=tables.
- **Streamlit** multi-page (`st.Page()` + `st.navigation()`), **Altair** charts,
  **PyDeck** maps (hexbin for dense point data like police calls).
- **`app_db.query()`** cached with `@st.cache_data(ttl=3600)` over a read-only
  DuckDB connection.
- **Dockerfile bakes the warehouse at build time** (Railway's release phase is a
  throwaway container, so the DB must be built into the image). The `.duckdb` file
  stays out of git and is rebuilt fresh on every deploy.
- **Railway** deploy from the `Dockerfile` — no Procfile, no `railway.toml`.
- **Toolchain:** `uv` only, `pytest` (TDD), `ruff`, `ty`, `prek`, `logging`,
  never wrap/hide errors, never push to `main`/`master`. (Full rules: `CLAUDE.md`.)

---

## 3. What changes: Vegas → Portland source mapping

This is the heart of the port. Each row is a topic; you must find the Portland
equivalent, confirm it's live, then wire it. **Verify every URL before coding** —
these are strong leads from domain knowledge, not guaranteed-current endpoints.
Treat "Portland lead" as a starting point for a quick check, not gospel.

| Topic | Elvis source (Vegas) | Portland lead | Notes / risk |
| --- | --- | --- | --- |
| **City GIS org** | ArcGIS `F1v0ufATbBQScMtY` (City of LV) | **PortlandMaps Open Data** (City of Portland ArcGIS Hub, `gis-pdx.opendata.arcgis.com`) | Primary spatial source. Find the ArcGIS org/services root. |
| **Regional GIS** | Henderson / Clark County ArcGIS | **Metro RLIS** (Regional Land Information System) | Regional layers spanning Multnomah/Washington/Clackamas. |
| **Police calls / crime** | LVMPD ArcGIS org, yearly layers | **Portland Police Bureau Open Data** (crime data CSV/ArcGIS on portland.gov / PortlandMaps) | PPB publishes crime data; may be CSV, not ArcGIS. Adjust `fetch_crime()`. |
| **Restaurant inspections** | SNHD developer ZIP bundle | **Multnomah County Environmental Health** food inspections | Confirm a machine-readable feed exists (portal/API/CSV). Higher risk. |
| **Fire inspections** | City of LV fire-prevention ArcGIS | Portland Fire & Rescue (if published) | May not exist openly → candidate to **drop**. |
| **Building permits** | City of LV permits ArcGIS (archived) | **Portland Permitting & Development** / PortlandMaps permits | Strong candidate; PortlandMaps has permits. |
| **Business licenses** | City of LV licenses ArcGIS | City of Portland Revenue/business registrations | Confirm availability; may differ in shape. |
| **Short-term rentals** | 3-jurisdiction ArcGIS | Portland **Accessory Short-Term Rental** permits | Portland regulates STRs; find the registry layer. |
| **Parks** | Metro-wide ArcGIS + water-feature join | **Portland Parks & Recreation** (PortlandMaps) | Strong candidate; reuse the water-feature flagging pattern. |
| **Marriage licenses** | Clark County CSVs (weddings.vegas rehost) | Multnomah County Recording | **High risk** — may not publish open CSVs like Clark County did → candidate to **drop** or replace. |
| **Tourism & Gaming** | LVCVA XLSX (visitors, ADR, gaming rev) | **Port of Portland** PDX passenger volumes + Travel Portland/hotel stats | **No gaming** in Portland — reframe as "Tourism / Air Travel." Drop gaming metrics. |
| **Signature water body** | Lake Mead elevation (USBR RISE) | **Willamette River gauge (USGS NWIS)** or **Bull Run** reservoir / Willamette basin reservoirs (USACE) | Pick one signature series. USGS NWIS river stage/flow is the easiest keyless swap. |
| **Weather extremes** | NOAA GHCN-Daily, Harry Reid Intl `USW00023169` | **NOAA GHCN-Daily, Portland Intl (PDX) `USW00024229`** | One-line station-code swap. Rename "Desert Heat" → e.g. "Rain & Records." |
| **Air quality** | EPA AQS bulk files, NV FIPS `32` / Clark `003` | **EPA AQS bulk files, OR FIPS `41` / Multnomah `051`** (optionally add Washington `067`, Clackamas `005`) | Same EPA bulk-file mechanism; just change FIPS. Keyless. |

**Net effect:** expect to keep ~8–11 pages, drop 1–3 that Portland lacks
(likely marriage, maybe fire), and reframe 2 (tourism-no-gaming, weather naming).
Always **`log()` what you drop** — a silently missing page reads as "done" when it
isn't. Final page list is a `TASKS.md` deliverable, not a guess made here.

---

## 4. Known gotchas (carry these over — they will bite otherwise)

1. **EPA AQS needs forced IPv4.** `aqs.epa.gov` hangs over IPv6 in some
   environments (Railway included). Elvis forces IPv4 for that host. Same host,
   same fix — **keep it.** (This is recorded in Evan's memory as the
   `elvis-ipv6-aqs-gotcha`.)
2. **Broken-TLS GIS servers.** Some municipal ArcGIS servers ship bad certs.
   Elvis passes `ssl_verify=False` for Clark County's `gisgate`. If a Portland
   endpoint has the same problem, reuse that path — **and log loudly that verify
   is disabled** for that host; never disable it globally.
3. **Warehouse must build at Docker build time, not runtime.** Do the
   `build_warehouse.py && dbt build` in the image build. Runtime just runs
   Streamlit. Don't try to fetch on cold start.
4. **The `.duckdb` file is large (~200 MB) and NOT in git.** `.gitignore` it;
   it's a build artifact rebuilt on every deploy.
5. **Encodings.** Muni/health/clerk bulk files are often Windows-1252 / cp1252,
   not UTF-8. Reuse Elvis's explicit-encoding readers.
6. **ArcGIS pagination + geometry.** Reproject to WGS84 (`out_sr=4326`) at fetch
   time so PyDeck maps just work; compute centroids for polygon layers.

---

## 5. Adaptation plan (the port, step by step)

Do the **vertical slice first** (one topic, end to end, deployed) before breadth —
same discipline Elvis's own task board used. `TASKS.md` breaks this into tracked
items; the shape is:

1. **Scaffold** the uv project (`uv init`; `uv add streamlit duckdb dbt-duckdb
   pandas pydeck altair openpyxl`; dev: `uv add --dev pytest ruff ty prek`).
   Copy Elvis's `app_db.py`, `dbt_project.yml`, `profiles.yml`, `Dockerfile`,
   `streamlit_app.py` skeleton; rename `vegas.duckdb` → `portland.duckdb` and the
   dbt `name`/`profile` `elvis` → `groening`.
2. **Create `city_config.py`** — all Portland endpoints, FIPS codes, station code,
   year ranges as constants. This is the one file that encodes "which city."
   `build_warehouse.py` imports from it (Elvis hardcoded these inline; centralize).
3. **Vertical slice:** pick one easy, high-confidence source (**Parks** or
   **Building Permits** via PortlandMaps, or **Air Quality** via EPA bulk with the
   FIPS swap). Fetch → one `stg_` view → one `mart_` table → one Streamlit page →
   run locally → deploy to Railway. Prove the whole pipe works.
4. **Fan out per topic** (§3 table): for each, verify the source, add a fetch call,
   a staging view, a mart, and a page. TDD the parser/transform logic with `pytest`
   fixtures in `conftest.py`. Drop topics with no source and log it.
5. **Overview page last** — headline metrics that read from the marts that exist.
6. **Deploy** to Railway; confirm the baked warehouse builds in the image and the
   app serves on `$PORT`.

---

## 6. Deliverables in this handoff

| File | What it is |
| --- | --- |
| [`PRIMER.md`](./PRIMER.md) | This document — the unified understanding + port plan. |
| [`PRD.md`](./PRD.md) | Product requirements for Groening (mirrors Elvis/portfolio PRD style). |
| [`TASKS.md`](./TASKS.md) | TDD task board: vertical slice first, then per-topic fan-out. |
| [`CLAUDE.md`](./CLAUDE.md) | House rules (verbatim) + Groening-specific build/repo notes. |

Drop these four files into the new repo's root. The `.duckdb`, `target/`, `logs/`,
`.venv/`, `__pycache__/` all belong in `.gitignore`.

---

## 7. The interview (unified understanding)

The primer is grounded in a live interview with Evan on 2026-08-11. **These four
answers are settled** and should not be re-opened without Evan:

| Question | Decision |
| --- | --- |
| **Target city/metro** | **Portland / Multnomah County** (Portland metro; extend to Washington + Clackamas where easy). |
| **Tech stack fidelity** | **Identical to Elvis** — DuckDB + dbt-duckdb + Streamlit + PyDeck/Altair, Docker→Railway, warehouse baked at build time. |
| **Dataset scope** | **Mirror Elvis where data exists** — target the same ~14 topics, drop what Portland lacks, add Portland-specific extras. |
| **Portfolio framing** | **Broader Data / Data-Engineering role** (not Analytics-Engineering-specific). Emphasize end-to-end ELT, multi-source ingestion, reproducible warehouse. |

### 7.1 Re-runnable interview protocol (for the receiving repo)

Scope can't be fully fixed until the new team confirms which Portland datasets are
actually live. When the receiving Claude session starts, **re-run this short
interview with Evan to close the remaining open questions** before committing the
page list:

1. **Codename** — keep `groening`, or pick another recognizable Portland figure?
2. **Metro breadth** — Multnomah only, or include Washington + Clackamas counties
   (and cities: Gresham, Beaverton, Hillsboro)? Affects GIS orgs + AQS FIPS list.
3. **Drop list** — confirm dropping topics with no Portland open feed (leading
   candidates: **Marriage Licenses**, possibly **Fire Inspections**). Any of these
   worth extra effort to source?
4. **Signature water body** — Willamette River (USGS NWIS gauge) vs. Bull Run /
   Willamette-basin reservoirs (USACE)? Which is the "Lake Mead" of Portland?
5. **Tourism reframe** — Port of Portland (PDX) passenger volumes as the anchor,
   plus Travel Portland/hotel stats? (Gaming is dropped — no analog.)
6. **Portland-specific extras** — anything Portland publishes that Vegas didn't and
   that would strengthen the piece (e.g. bike/transit counts, tree canopy, 311
   requests, homelessness/point-in-time, urban-growth-boundary)?
7. **Deploy target** — Railway (as Elvis), or does Evan want it under the portfolio
   orchestrator + an `*.evanappel.me` subdomain?

Record the answers at the top of `TASKS.md` (an "Interview outcomes" block) so the
scope is captured where the work is tracked. Do not start coding pages until #2,
#3, and #4 are answered — they change the source list.
