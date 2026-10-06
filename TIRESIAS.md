# Tiresias

The "Ask Tiresias" page is a grounded text-to-SQL agent over the Portland marts. It
cites its SQL and abstains when it can't ground an answer in a real row. Engine:
https://github.com/EvanWAppel/tiresias (pinned in `pyproject.toml` / `requirements.txt`).
Groening keeps only its city config:

- `tiresias.yml`: allowed tables, map-only columns, examples, planner notes,
  grounding threshold (with calibration notes), limits.
- `metrics.yml`: governed metric registry (empty for now).
- `evals/tiresias_gold.yaml`, `evals/tiresias_retrieval_gold.yaml`: gold sets.

```
uv run tiresias check                    # config vs dbt artifacts
uv run tiresias eval --retrieval-only    # recall@k, no key needed
uv run --env-file .env tiresias eval     # + live gold set (needs a dedicated key)
uv run tiresias calibrate                # pick the grounding threshold
```

The page needs `ANTHROPIC_API_KEY` from a dedicated, spend-capped workspace key;
without it the page shows a notice and stops.

## Column-doc claims to check against the data

The mart column docs (`models/marts/schema.yml`) were written from code, not from
the data. These claims could not be established from code; each says how to check.

1. Timestamps (`mart_crime_by_hour_weekday.reported_hour`, crime `month`, service
   request dates, permit `issue_month`): described as likely UTC (ArcGIS epoch ms
   converted with no timezone step). Check a known incident's local time, or
   whether the hour histogram peaks around 2–6 UTC.
2. `mart_crime_*.crime_against`: assumed Person / Property / Society. Check distinct values.
3. `mart_bike_*`: "active" = `year_retired` is null; `Status` is not filtered, so
   planned segments may be included. Check distinct `Status`.
4. `mart_trees_*`: source is the "Parks Tree Inventory" layer, but docs call it a
   street-tree inventory. Check the publisher's metadata.
5. `mart_trees_by_species.native`: assumed 'Yes'/'No' text. Check distinct values.
6. `mart_historic_*`: demolished resources not filtered. Count by `demolished` in `stg_historic`.
7. `mart_heritage_summary.first_year`: may include implausible years (≤1900). Check `min(year_designated)`.
8. `mart_heritage_*` diameter assumed inches (from the staging name).
9. `mart_marriage_annual.same_sex`: null where a year's sheet lacks it (probably pre-2014).
10. `mart_tourism_*.passengers`: BTS "total" taken as all international passengers.
11. `mart_build_metadata.built_at`: UTC vs local after the cast (table is excluded from Tiresias).
12. `mart_inspections_recent`: one row per permit, latest inspection; value sets of
    `permit_type`, `inspection_type`, `purpose` unknown.
13. `mart_short_term_rentals.application_number`: may not be unique.
14. `mart_willamette_daily.discharge_cfs`: tidal site; values could be negative (not claimed).
