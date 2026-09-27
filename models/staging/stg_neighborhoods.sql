-- Portland neighborhood boundaries: one row per polygon with the name and its
-- outer ring (WGS84) as a JSON coordinate array. The choropleth base layer.

with source as (
    select * from {{ source('raw', 'neighborhoods') }}
)

select
    trim(name)    as name,
    boundary_json
from source
where name is not null and trim(name) <> ''
