# Target a new metro

Groening, Elvis (Las Vegas) and Robbins (Seattle) are independent ports of one
architecture: `build_warehouse.py` lands public data in DuckDB `raw.*` tables,
dbt models it into `staging` views and `marts` tables, and Streamlit pages read
the marts. The only per-city surface is **`city_config.py`**.

This guide turns that claim into a runnable procedure. It was chosen over a
shared pip package on 2026-09-27 (see `DECISIONS.md`): three working apps don't
need a cross-repo versioning surface, and a scaffold delivers most of the "new
cities are cheap" value.

## 1. Stamp the skeleton

From this repo:

```sh
make new-city DEST=../robbins CODENAME=robbins CITY="Seattle, WA" DB=seattle
```

or directly: `uv run python new_city.py ../robbins --codename robbins --city "Seattle, WA" --db seattle`.

| Argument | Meaning | Rule |
| --- | --- | --- |
| `DEST` | new project directory | must be absent or empty (nothing is overwritten) |
| `CODENAME` | project + dbt project/profile name | lowercase, digits, `_`; starts with a letter |
| `CITY` | display name for the app and docs | non-blank |
| `DB` | DuckDB file stem (`<DB>.duckdb`) and dbt source database | same rule as `CODENAME` |

What lands:

| File | What it is |
| --- | --- |
| `city_config.py` | Stub: `CITY_NAME`, fetch tuning, empty `SOURCES` / `DROPPED_TOPICS`, and `source_catalog_rows()` copied from Groening. |
| `build_warehouse.py` | The city-agnostic engine copied **verbatim** from Groening (`fetch_layer`, `fetch_features`, `_centroid`, `_epoch_to_date`, `_urlopen` with retries, `_ssl_ctx`, IPv4-first, `load_raw`, build provenance) plus an empty `FETCHERS` registry and a `main()` that refuses to build with no sources. |
| `models/` | dbt sources stub plus the generic `stg_build_metadata` → `mart_build_metadata` pair. |
| `streamlit_app.py`, `app_db.py`, `views/overview.py` | One-page app: build provenance + the source catalog. |
| `tests/test_city_config.py` | Catalog contract: every entry complete, every `FETCHERS` key catalogued. |
| `Dockerfile`, `requirements.txt`, `pyproject.toml`, `.gitignore`, `.python-version`, `README.md`, `BLOCKED.md` | Project furniture. |

The engine copy is a snapshot. Groening's `build_warehouse.py` stays the
reference: a fix made there is not pushed to stamped projects, and that's the
cost of the scaffold-over-package decision. Re-copy a helper by hand if it matters.

## 2. Set up the project

```sh
cd ../robbins
git init
uv add streamlit duckdb dbt-duckdb pandas pydeck altair openpyxl
uv add --dev pytest ruff ty prek pyyaml
uv run python -m pytest -q   # the catalog contract passes on the empty stub
```

Copy `CLAUDE.md` / `AGENTS.md` from Groening and swap the city-specific notes.
Apply branch protection as soon as the repo is public.

## 3. Interview, then fill in `city_config.py`

Before wiring anything, settle the questions that change the source list (Groening
`PRIMER.md` §7.1): metro breadth (which counties: they set the EPA AQS FIPS list),
the drop list, the signature water body, and the tourism reframe. Then, for each
topic in the Elvis blueprint, find the local equivalent and **verify it's live
and machine-readable** before writing code:

| Topic | What to find | Config constants |
| --- | --- | --- |
| Weather | NOAA GHCN-Daily station id for the main airport | `NOAA_STATION` |
| Air quality | State + county FIPS for EPA AQS bulk files | `AQS_STATE`, `AQS_COUNTIES` |
| River / reservoir | USGS NWIS site or USBR RISE series | e.g. `USGS_SITE` |
| Permits, parks, crime, … | ArcGIS FeatureServer/MapServer layer URLs | `<TOPIC>_LAYER_URL` |

Anything the metro does not publish openly goes in `DROPPED_TOPICS` with a
one-line reason. The build logs each one, so a missing page never reads as done.

## 4. Vertical slice: one topic end to end

Pick the easiest verified source (an ArcGIS parks layer is usually it):

1. **Test first.** Write a pytest for any parsing/transform logic beyond a plain
   `fetch_layer` call, with fixtures in `tests/conftest.py`.
2. **Fetch.** In `build_warehouse.py`:
   ```python
   def fetch_parks() -> pd.DataFrame:
       return fetch_layer(cfg.PARKS_LAYER_URL, centroid=True)

   FETCHERS = {"parks": fetch_parks}
   ```
3. **Catalog.** Add a `SOURCES["parks"]` entry with all seven fields (title,
   page, publisher, url, coverage, grain, license). The contract test fails
   until you do.
4. **Model.** Add `parks` to `models/staging/sources.yml`, then
   `models/staging/stg_parks.sql` (light normalization) and
   `models/marts/mart_parks.sql` (viz-ready), with `not_null`/`unique` tests on
   the grain key in a `schema.yml`.
5. **Page.** `views/parks.py` reading `main.mart_parks` via `app_db.query()`, and
   register it in `streamlit_app.py`.
6. **Build and run.**
   ```sh
   uv run python build_warehouse.py && uv run dbt build --profiles-dir .
   uv run streamlit run streamlit_app.py
   ```

A zero-row fetch raises in `load_raw`. That's deliberate, so don't catch it.

## 5. Fan out, then the Overview

Repeat step 4 per topic. Groening's own fetchers are worked examples for the
awkward cases: EPA AQS bulk zips (`fetch_air_quality`), NOAA GHCN CSVs
(`fetch_weather`), USGS NWIS JSON (`_parse_usgs_dv`), GTFS zips (`_parse_gtfs`),
cp1252 bulk files, and polygon point-in-polygon tagging for choropleths
(`tag_neighborhoods`). Write the Overview's headline numbers last, from whichever
marts exist.

## 6. Known gotchas (they carry across cities)

- **EPA AQS over IPv6 hangs.** The IPv4-first patch in the engine handles it. Keep it.
- **Broken-TLS municipal servers.** Pass `ssl_verify=False` for that one host
  only. The engine logs a warning every time.
- **Bake the warehouse at Docker build time.** Release phases run in throwaway
  containers. The `.duckdb` file stays out of git.
- **Some APIs 403 datacenter egress** (Groening's restaurant inspections). Commit a
  snapshot fallback and log loudly when it's used.
- **Encodings.** Clerk and health bulk files are often cp1252, so use `cfg.BULK_ENCODING`.

## 7. Deploy

Railway from the `Dockerfile`, with no Procfile or `railway.toml`. Merging to
`main` deploys, so merges go through PRs. The app needs no secrets: everything is
public data. If you add an LLM feature, its key must be a dedicated, spend-capped
workspace key, never a personal one.
