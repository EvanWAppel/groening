-- Build provenance: one row per loaded raw table, with a shared build timestamp.

with source as (
    select * from {{ source('raw', 'build_metadata') }}
)

select
    table_name,
    try_cast(row_count as bigint)         as row_count,
    try_cast(built_at as timestamp)        as built_at
from source
