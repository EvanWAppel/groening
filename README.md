# Groening: a city-agnostic open-data pipeline

Groening is an interactive **Streamlit** app over a **DuckDB** warehouse built with
**dbt**. It ingests free public datasets about the Portland, OR metro (Multnomah,
Washington, and Clackamas counties) and presents them as maps, charts, and
searchable tables. Thirteen datasets, from building permits to river flow, each
wired end to end from a live public source to a mart to a page.

The point of interest for a reviewer is not Portland. It is that the whole pipeline
is parameterized: the same engine runs on Las Vegas
([Elvis](https://github.com/EvanWAppel/elvis)) and Seattle
([Robbins](https://github.com/EvanWAppel/robbins)) data. Re-targeting to a new
metro is one file, not a rewrite. See "The one-file city swap" below.

**Live demo:** `groening.evanappel.me` (deploying). Screenshots below. No login.

## What this demonstrates

For an Analytics or Data Engineering reviewer, in one screen:

- **Parameterized ELT.** Every city-specific value (ArcGIS endpoints, EPA AQS FIPS
  codes, NOAA station, USGS gauge, year ranges) lives in one `city_config.py`
  module. Swapping cities is an edit to that file, not a fork of the codebase.
- **Medallion modeling in dbt.** `build_warehouse.py` lands raw public data in
  `raw.*` tables; dbt models it into `staging` views (light normalization) and
  `marts` tables (viz-ready aggregations). Staging is views, marts are tables.
- **Data-quality discipline.** A fetch that returns zero rows raises rather than
  shipping a silently empty page. Broken-TLS hosts are handled per host and logged,
  never disabled globally. The dbt build gates every mart before the app can read it.
- **Modern Python toolchain.** `uv` for dependencies, `ruff` for lint, `ty` for
  types, `pytest` for TDD on every parser and transform, `prek` for pre-commit.
- **Reproducible deploy.** A Docker build bakes the warehouse at build time, so the
  runtime container just serves Streamlit. The database is a rebuilt-on-deploy
  artifact, never committed.

## The one-file city swap

The reason three metros run on one codebase is `city_config.py`. It holds the
ArcGIS org and service paths, the EPA AQS state and county FIPS codes, the NOAA
GHCN station, the USGS river gauge, and the source URLs and year ranges for the
target city. `build_warehouse.py` imports from it and knows nothing else about
which city it is fetching. Point that one file at a new metro's open-data portals
and the same staging views, marts, and Streamlit pages light up on the new data.

That is the durable engineering claim here: the pipeline is a template, and a city
is a configuration of it.

## Architecture

```
city_config.py       → the only "which city" file (endpoints, FIPS, gauges, ranges)
        ↓
build_warehouse.py   → raw.* DuckDB tables        (ELT fetch from public sources)
        ↓ dbt build
models/staging/*.sql → views   (light normalize)
models/marts/*.sql   → tables  (viz-ready aggregations)
        ↓
views/*.py (Streamlit) read the marts via app_db.query()
```

Charts are Altair. Maps are PyDeck, with 3D hexbins for dense point layers like
permits, crime, and the street-tree inventory.

## The datasets

Thirteen topics, each fetch to mart to page: Building Permits, Parks, Reported
Crime, Short-Term Rentals, Restaurant Inspections, Willamette River flow, Rain and
Records, Air Quality, Street Trees, Bike Network, Air Travel, Marriages, and the
Urban Growth Boundary. Topics that Portland does not publish in a machine-readable
form were dropped and logged rather than faked. The Overview page reads a headline
number from each mart and links into its detail page.

## How it was built

Groening was designed, built, and shipped on my own time using agentic
command-line tooling, primarily Claude Code. The working loop was consistent:
write the requirements, let the agent execute, check the result against a test,
and loop until it holds. Every parser and transform was built test-first with
`pytest`. The agent moved fast; the tests are what made the speed safe.

## Run locally

```bash
uv sync
uv run python build_warehouse.py            # fetch public sources -> portland.duckdb
uv run dbt build --profiles-dir .           # build staging views + mart tables
uv run streamlit run streamlit_app.py       # serve on :8501
```

## Deploy

Railway builds from the `Dockerfile`, which runs `build_warehouse.py && dbt build`
at build time so the runtime container only serves Streamlit on `$PORT`. The
`*.duckdb` file is a git-ignored build artifact, rebuilt on every deploy. No
secrets: every source is public, and `$PORT` is injected by the platform.

## About

Built by Evan Appel, a data and analytics engineer by profession and an
agent-native developer by practice. I build software with AI agents and keep it
honest with tests.

- Portfolio: [evanappel.me/projects](https://evanappel.me/projects)
- GitHub: [github.com/EvanWAppel](https://github.com/EvanWAppel)
- LinkedIn: [evanwebsterappel](https://www.linkedin.com/in/evanwebsterappel)
- Email: appelew@gmail.com
