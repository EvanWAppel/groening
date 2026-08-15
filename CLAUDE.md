prime directive: don't do anything you're unclear about, ask me about it.
use uv
run python tools with uv run python
do not edit pyproject.toml dependencies directly
use uv add LIB or uv add --dev LIB
use pytest to implement tdd
use pytest fixtures in conftest.py to DRY
use ruff to lint
use ty to typecheck
use prek for precommits
use logging to help ai debug
do not hide or wrap errors.
Do not push to master or main

# Groening — project notes

Groening is a Portland-metro open-data explorer: a near-exact port of the Elvis
(Las Vegas) app. Read PRIMER.md first, then PRD.md and TASKS.md.

## Architecture (identical to Elvis — do not redesign)
- ELT: `build_warehouse.py` fetches public data into `raw.*` tables in a single
  DuckDB file, then `dbt build` (dbt-duckdb) models `staging/` views and `marts/`
  tables. Streamlit pages read the marts.
- App: `streamlit_app.py` (st.Page + st.navigation) routes to `views/*.py`; each
  page queries via the cached `app_db.query()` helper (@st.cache_data).
- Charts: Altair. Maps: PyDeck (hexbin for dense point layers).

## City config
- ALL Portland-specific values (ArcGIS orgs/services, EPA AQS state/county FIPS,
  NOAA station code, source URLs, year ranges) live in `city_config.py`.
  `build_warehouse.py` imports from it. Swapping cities = editing that one file.

## Build & deploy
- The DuckDB warehouse is baked at DOCKER BUILD TIME (`build_warehouse.py &&
  dbt build --profiles-dir .`), never at runtime. Railway's release phase is a
  throwaway container.
- The `*.duckdb` file is a build artifact — git-ignore it; it's rebuilt on every
  deploy. Also ignore `target/`, `logs/`, `.venv/`, `__pycache__/`.
- Deploy to Railway from the Dockerfile (no Procfile, no railway.toml). Runtime
  serves Streamlit on `$PORT` (default 8501 locally).

## Known gotchas (carry over from Elvis)
- Force IPv4 for `aqs.epa.gov` — it hangs over IPv6 in some environments
  (Railway included). Air quality uses keyless EPA bulk files.
- Some municipal ArcGIS servers ship broken TLS certs; pass `ssl_verify=False`
  ONLY for the specific offending host, and log a warning when you do. Never
  disable verification globally.
- Muni/health/clerk bulk files are often Windows-1252 / cp1252, not UTF-8.
- Reproject ArcGIS geometry to WGS84 (out_sr=4326) at fetch time; compute
  centroids for polygon layers so PyDeck maps just work.

## Data discipline
- Verify every source is live and machine-readable before wiring it. The primer's
  Portland leads are starting points, not guarantees.
- A fetch that returns zero rows should raise, not silently ship an empty page.
- Drop any topic Portland doesn't publish — and `log()` the drop so it's visible.
