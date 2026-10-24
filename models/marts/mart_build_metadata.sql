{{ config(materialized='table') }}

-- Per-source build provenance: one row per loaded raw table. The "Data as of
-- <date> · N sources · M rows" banner aggregates this (max built_at, count of
-- rows, sum of row_count); the Sources & Methodology page reads it row by row.
-- from_snapshot / snapshot_as_of flag a topic served from its last good snapshot
-- because the live source failed; its page shows a "data as of" notice.

select
    table_name,
    row_count,
    built_at,
    from_snapshot,
    snapshot_as_of
from {{ ref('stg_build_metadata') }}
order by table_name
