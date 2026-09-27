{{ config(materialized='table') }}

-- Per-neighborhood historic-resource counts for the choropleth map: one row per
-- neighborhood polygon with its boundary ring (WGS84) and the number of surveyed
-- historic resources that fell inside it (0 where none). hood_name is assigned at
-- build time by point-in-polygon, so this is a plain GROUP BY joined to boundaries.

with counts as (
    select hood_name as name, count(*) as n
    from {{ ref('stg_historic') }}
    where hood_name is not null
    group by 1
)

select
    nb.name          as neighborhood,
    nb.boundary_json,
    coalesce(c.n, 0) as n
from {{ ref('stg_neighborhoods') }} nb
left join counts c on c.name = nb.name
