-- Build provenance: one row per loaded raw table, with a shared build timestamp.
-- snapshot_as_of is set only for a table whose live fetch failed this build and
-- that was served from its last good snapshot in data/ (DECISIONS.md 2026-10-24).

with source as (
    select * from {{ source('raw', 'build_metadata') }}
)

select
    table_name,
    try_cast(row_count as bigint)         as row_count,
    try_cast(built_at as timestamp)        as built_at,
    source.snapshot_as_of is not null      as from_snapshot,
    try_cast(source.snapshot_as_of as timestamp) as snapshot_as_of
from source
