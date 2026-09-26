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
