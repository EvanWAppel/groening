# Groening — PRD

> **Status:** Draft v1 · **Owner:** Evan Appel · **Date:** 2026-08-11
> A Portland-metro open-data explorer. A near-exact port of **Elvis** (Las Vegas)
> to Portland, OR. See [`PRIMER.md`](./PRIMER.md) for the handoff context and the
> Vegas→Portland source mapping; this document specifies the product.

---

## 1. Problem

Portland-area public data is scattered across a dozen portals and agencies —
PortlandMaps, Metro RLIS, Portland Police Bureau, Multnomah County, EPA, NOAA,
USGS — in inconsistent formats (ArcGIS FeatureServers, CSV bundles, XLSX, bulk
files). There is no single place to browse the region's civic data as maps,
trends, and searchable tables. Separately, Evan needs a **portfolio piece** that
demonstrates end-to-end data engineering: multi-source ingestion, a reproducible
warehouse, dbt modeling, and an interactive app.

## 2. Goals

1. **One explorer for Portland-metro public data** — maps, charts, and searchable
   tables across the region's most useful open datasets, in one Streamlit app.
2. **Reproducible, hands-off pipeline** — a single `build_warehouse.py` fetch +
   `dbt build` recreates the entire warehouse from public sources on every deploy.
3. **Portfolio proof for a Data / Data-Engineering role** — showcase ELT
   orchestration, multi-source ingestion, dbt staging/marts modeling, and
   deployment, not just a chart. (Framing decided in the interview: broad Data/DE,
   not Analytics-Engineering-specific.)
4. **Cheap to run, easy to redeploy** — embedded DuckDB, no database server, no
   secrets, warehouse baked into the image at build time.

## 3. Non-goals

- **Not a real-time system.** Data is as fresh as the last deploy/build. No live
  streaming, no runtime fetches.
- **Not a new stack.** The stack is **identical to Elvis** by decision — no
  reevaluating DuckDB/dbt/Streamlit/Railway. (Interview: "Identical stack.")
- **Not a shared design system with other portfolio apps.** Groening has its
  own look, like every other project under `evanappel.me`.
- **No secrets / no auth.** Public data only; nothing to protect.
- **Not exhaustive.** Mirror Elvis's topics where Portland publishes them; drop the
  rest rather than forcing thin or unreliable sources.

## 4. Principles & constraints

- **Port, don't reinvent.** Elvis's architecture, fetch helpers, dbt layout, and
  Dockerfile are the blueprint. Change data sources and city config; keep patterns.
- **One config surface.** All city-specific values (endpoints, FIPS codes, station
  code, year ranges) live in `city_config.py`. Swapping cities = editing one file.
- **Warehouse is built at Docker build time**, never at runtime. The `.duckdb`
  file is a git-ignored build artifact.
- **Honor the house style** (`CLAUDE.md`): `uv`, `uv run python`, `ruff` + `ty` +
  `prek` + `pytest`, dependencies only via `uv add`, don't hide or wrap errors, use
  `logging`, never push to `main`/`master`.
- **Verify every source before wiring it.** The Portland leads in the primer are
  starting points; confirm each is live and machine-readable, and `log()` any topic
  dropped for lack of a source.
- **dbt two-tier is the analytics contract:** `staging/` views normalize raw
  schemas; `marts/` tables aggregate/denormalize for the app. Pages read marts only.

## 5. Scope — topic inventory (target)

Mirror of Elvis, adjusted for Portland. Final status per topic is confirmed in
`TASKS.md` after source verification; this is the plan.

| # | Page | Portland source (lead) | Status |
| --- | --- | --- | --- |
| 1 | **Overview** | Derived from the marts that exist | Keep |
| 2 | **Building Permits** | Portland Permitting & Development / PortlandMaps | Keep (high confidence) |
| 3 | **Parks** | Portland Parks & Recreation (PortlandMaps) + water-feature flags | Keep (high confidence) |
| 4 | **Air Quality** | EPA AQS bulk files, OR FIPS 41 / Multnomah 051 (+ Washington, Clackamas) | Keep (high confidence) |
| 5 | **Weather (Rain & Records)** | NOAA GHCN-Daily, PDX `USW00024229` | Keep (rename from "Desert Heat") |
| 6 | **Police / Crime Calls** | Portland Police Bureau open crime data | Keep (verify format) |
| 7 | **Short-Term Rentals** | Portland Accessory Short-Term Rental permits | Keep (verify) |
| 8 | **Business Licenses / Registrations** | City of Portland Revenue | Keep (verify) |
| 9 | **Restaurant Inspections** | Multnomah County Environmental Health | Keep if feed exists (risk) |
| 10 | **Signature Water Body** | Willamette River (USGS NWIS) or Bull Run (USACE) | Keep (pick one — interview #4) |
| 11 | **Tourism / Air Travel** | Port of Portland (PDX) passengers + Travel Portland | Reframe (drop gaming) |
| 12 | **Public Art** | PortlandMaps public art (if published) | Verify / optional |
| 13 | **Fire Inspections** | Portland Fire & Rescue (if published) | Candidate to drop |
| 14 | **Marriage Licenses** | Multnomah County Recording | Candidate to drop (risk) |
| + | **Portland extras** | e.g. 311 requests, tree canopy, bike/transit counts, UGB | Optional — interview #6 |

## 6. Key decisions (decision log)

| # | Decision | Rationale |
| --- | --- | --- |
| D1 | **Port Elvis, don't design fresh.** | Battle-tested architecture; fastest path to a working, credible portfolio piece. |
| D2 | **Identical stack** (DuckDB + dbt-duckdb + Streamlit + PyDeck/Altair). | Interview decision; reuse patterns and helpers wholesale. |
| D3 | **Target Portland / Multnomah metro.** | Interview decision. Rich open-data ecosystem (PortlandMaps, Metro RLIS, PPB). |
| D4 | **Mirror Elvis's topics where data exists; drop the gaps.** | Interview decision. Breadth where cheap; no thin/unreliable sources. |
| D5 | **Centralize city config in `city_config.py`.** | Elvis hardcoded endpoints inline; a single config surface makes the port (and future cities) a one-file change. |
| D6 | **Warehouse baked at Docker build time; `.duckdb` git-ignored.** | Railway release phase is throwaway; predictable cold starts; reproducible from public sources. |
| D7 | **No gaming page; reframe Tourism around PDX air travel.** | Portland has no gaming analog to LVCVA; Port of Portland publishes passenger volumes. |
| D8 | **Broad Data/DE portfolio framing.** | Interview decision. Emphasize end-to-end ELT and multi-source ingestion. |
| D9 | **Keep the Vegas gotchas that still apply** (force IPv4 for EPA AQS; `ssl_verify=False` only for specific broken-TLS hosts, logged). | Same EPA host; municipal GIS servers still ship bad certs. |

## 7. Architecture

Identical to Elvis (see `PRIMER.md` §1). Repo layout:

```
groening/
├── build_warehouse.py     # ETL: fetch every source -> raw.* DuckDB tables (imports city_config)
├── city_config.py         # ALL Portland-specific constants (the "which city" file)
├── streamlit_app.py       # multi-page router (st.Page + st.navigation)
├── app_db.py              # read-only DuckDB connection + @st.cache_data query()
├── dbt_project.yml        # name/profile: groening ; staging=view, marts=table
├── profiles.yml           # dbt-duckdb, path -> portland.duckdb
├── Dockerfile             # build: build_warehouse.py && dbt build ; run: streamlit on $PORT
├── requirements.txt       # pip fallback for Docker
├── pyproject.toml / uv.lock
├── models/
│   ├── staging/           # stg_*.sql views + sources.yml
│   └── marts/             # mart_*.sql tables
├── views/                 # one *.py Streamlit page per kept topic
├── tests/                 # pytest; conftest.py fixtures (DRY)
└── portland.duckdb        # build artifact; NOT in git
```

**Data flow:** `build_warehouse.py` (build time) → `raw.*` → `dbt build` →
`staging` views → `marts` tables → Streamlit reads marts at runtime via
`app_db.query()`.

## 8. Configuration & secrets

- **No secrets.** All data is public.
- **`city_config.py`** holds every city-specific value: ArcGIS org/service roots
  (PortlandMaps, Metro RLIS, PPB, Multnomah), EPA AQS state/county FIPS, NOAA
  station code, source URLs, and available year ranges.
- Runtime needs only `$PORT` (injected by Railway; default `8501` locally).

## 9. Deployment

- **Railway**, from the `Dockerfile`. No Procfile, no `railway.toml`.
- Build stage runs `build_warehouse.py && dbt build --profiles-dir .`, baking
  `portland.duckdb` into the image (5–10 min depending on data volumes).
- Runtime: `streamlit run streamlit_app.py --server.port ${PORT:-8501}
  --server.address 0.0.0.0`.
- **Optional (interview #7):** register under the portfolio orchestrator manifest
  and expose at `groening.evanappel.me`.

## 10. Success metrics

- **Reproducible:** a clean `uv sync && uv run python build_warehouse.py &&
  uv run dbt build --profiles-dir . && uv run streamlit run streamlit_app.py`
  produces the full app locally.
- **Deployed:** live on Railway, warehouse baked in the image, serving on `$PORT`.
- **Coverage:** ≥ 8 working topic pages, each reading a real Portland dataset; every
  dropped topic explicitly logged with its reason.
- **Portfolio-ready:** README explains the ELT + dbt + Streamlit story for a
  Data/DE audience.

## 11. Open questions

Resolve via the re-runnable interview in `PRIMER.md` §7.1 before finalizing the
page list:

1. Metro breadth — Multnomah only vs. + Washington + Clackamas (affects GIS orgs +
   AQS FIPS list).
2. Confirm the drop list (Marriage Licenses; possibly Fire Inspections).
3. Signature water body — Willamette River (USGS NWIS) vs. Bull Run / basin
   reservoirs (USACE).
4. Portland-specific extra datasets worth adding (311, tree canopy, transit counts…).
5. Deploy target — standalone Railway vs. under the portfolio orchestrator +
   `*.evanappel.me` subdomain.

### Resolved (from interview, 2026-08-11)

- **City** = Portland / Multnomah metro.
- **Stack** = identical to Elvis.
- **Scope** = mirror Elvis where data exists.
- **Framing** = broad Data / Data-Engineering portfolio piece.
- **Codename** = `groening` (bikeable).

---

## 12. Phase 2 — portfolio enhancements (backlog)

The v1 goal (a working, deployed, tested explorer) is met. This phase sharpens the
piece **for a Data/DE reviewer**. The theme: the strongest engineering claims —
parameterized ELT, medallion modeling, data-quality tests, one-template-per-city —
currently live in the README and the code but are **invisible in the running app**.
Phase 2 makes them visible, then leans into the multi-city template that is the
durable differentiator. Items are proposed, not committed; each with a real
trade-off gets a `DECISIONS.md` entry before it's built.

### 12.1 Prove the pipeline (highest signal, mostly leverages existing work)

- **E1 — Sources & Methodology page.** One in-app table: each dataset → source URL,
  publisher, license, coverage window, row count, and the raw→staging→mart
  transform applied. Includes the **dropped** topics and why (licenses, public art,
  fire, 311) — provenance and honesty are the point. Most of this data already
  exists in `city_config.py`, `sources.yml`, and the drop logs.
- **E2 — Data-freshness / build-provenance banner.** Stamp the build timestamp,
  source count, and total row count into a metadata table during
  `build_warehouse.py`; surface "Data as of \<date\>" globally. Turns the
  baked-at-build-time constraint into a visible feature.
- **E3 — dbt lineage, exposed.** Declare each Streamlit page as a **dbt exposure**
  so lineage is source→staging→mart→page-complete, then surface it: link the
  static `dbt docs` DAG, or render lineage from `manifest.json` on an "Under the
  hood" page. Backs up the medallion claim visually.
- **E4 — Data-quality summary in-app.** Read `run_results.json` after `dbt build`
  and show a passing-test count (not_null / unique / accepted_values). The tests
  already run; this proves it to a reviewer who never opens the repo.

### 12.2 Lean into the multi-city template (the differentiator)

- **E5 — Cross-city comparison.** DuckDB `ATTACH` (read-only) of the Portland,
  Vegas (Elvis), and Seattle (Robbins) warehouses, comparing shared marts (weather,
  air quality, permits). Proves the marts are genuinely parameter-compatible across
  cities — the honest demonstration of the template claim. May be a page here or a
  small standalone "trilogy" app. **Trade-off to log:** where the comparison lives,
  and how the three `.duckdb` artifacts are co-located at build/deploy time.
- **E6 — Extract the shared engine.** Factor the common fetch helpers + app
  scaffolding out of Elvis/Robbins/Groening into a pip-installable package that all
  three depend on, with `city_config.py` as the only per-city surface. Highest
  effort (touches three repos). **Lighter alternative to consider first:** a
  documented `make new-city` scaffold + a "target a new metro" guide that makes the
  one-file-swap claim runnable. **Decision required** before starting: full package
  vs. scaffold-and-guide.

### 12.3 Portland-specific data expansion (breadth)

- **E7 — New standout datasets** Vegas lacked, each one fetch→mart→page: **TriMet
  GTFS** (transit), **311 / PDX service requests**, **tree-canopy change over
  time**, or **housing/eviction** data. (Note: row-level 311 was HELD in v1 —
  sensitive campsite-complaint data; pick a non-sensitive feed or aggregate.)

### 12.4 Ambitious / optional

- **E8 — Serving layer.** Expose the marts as a small read-only JSON API (FastAPI
  over the same DuckDB). Shows a data *product*, not just a dashboard.
- **E9 — Natural-language query over the marts** (text-to-SQL). **BLOCKED on the
  personal-key guardrail:** a public deploy backed by an LLM must use a dedicated
  isolated workspace + a scoped, spend-capped key — never Evan's personal/default
  Anthropic key. Do not wire this until that checklist (see global `CLAUDE.md`) is
  satisfied and Evan confirms. Tracked in `BLOCKED.md`.
