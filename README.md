# Groening — Portland-Metro Open-Data Explorer

An interactive, multi-page **Streamlit** app over a **DuckDB** warehouse built with
**dbt**, ingesting free public datasets about the **Portland, OR metro**
(Multnomah + Washington + Clackamas) and presenting them as maps, charts, and
searchable tables. A Portland port of [Elvis](https://github.com/EvanWAppel/elvis)
(Las Vegas) — same architecture, Portland data.

## Architecture

```
build_warehouse.py  → raw.* DuckDB tables   (ELT fetch from public sources)
        ↓ dbt build
models/staging/*.sql → views  (light normalize)
models/marts/*.sql   → tables (viz-ready aggregations)
        ↓
views/*.py (Streamlit) read the marts via app_db.query()
```

- **ELT:** `build_warehouse.py` fetches each public source into `raw.*` tables in
  a single `portland.duckdb` file; `dbt build` models staging views + mart tables.
- **App:** `streamlit_app.py` (`st.Page` + `st.navigation`) routes to `views/*.py`.
  Charts are Altair; maps are PyDeck (hexbin for dense point layers).
- **Config:** every Portland-specific value (ArcGIS endpoints, EPA AQS FIPS, NOAA
  station, USGS gauge) lives in `city_config.py` — the one "which city" file.

## Run locally

```bash
uv sync
uv run python build_warehouse.py            # fetch → portland.duckdb
uv run dbt build --profiles-dir .           # build staging + marts
uv run streamlit run streamlit_app.py       # serve on :8501
```

## Deploy

Railway builds from the `Dockerfile`, which bakes the warehouse at **build time**
(`build_warehouse.py && dbt build`) so the runtime container just serves Streamlit
on `$PORT`. The `*.duckdb` file is a git-ignored build artifact, rebuilt each deploy.

## Status

Vertical slice shipped: **Building Permits** (PortlandMaps, ~36k geocoded permits).
See `TASKS.md` for the topic fan-out board and `PRD.md` for the product spec.
