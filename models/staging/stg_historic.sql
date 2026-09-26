-- City Historic Resource Inventory: normalize style/rank, parse the free-text
-- YEAR_BUILT ("ca. 1907", "1945-1951") to a 4-digit year, and bound out-of-range
-- values (some rows carry bad years). "rank" is a reserved word -> significance_rank.

with source as (
    select * from {{ source('raw', 'historic') }}
),

parsed as (
    select
        try_cast(resource_id as integer)                     as resource_id,
        orig_name,
        coalesce(nullif(trim(style), ''), 'Unspecified')     as style,
        coalesce(nullif(trim("rank"), ''), 'unranked')       as significance_rank,
        resource_type,
        neighborhood,
        architect,
        demolished,
        try_cast(regexp_extract(year_built, '[0-9]{4}') as integer) as year_raw,
        longitude,
        latitude
    from source
)

select
    resource_id,
    orig_name,
    style,
    significance_rank,
    resource_type,
    neighborhood,
    architect,
    demolished,
    case when year_raw between 1800 and 2026 then year_raw end as year_built,
    longitude,
    latitude
from parsed
