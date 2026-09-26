{{ config(materialized='table') }}

-- Per-source build provenance: one row per loaded raw table. The "Data as of
-- <date> · N sources · M rows" banner aggregates this (max built_at, count of
-- rows, sum of row_count); the Sources & Methodology page reads it row by row.

select
    table_name,
    row_count,
    built_at
from {{ ref('stg_build_metadata') }}
order by table_name
