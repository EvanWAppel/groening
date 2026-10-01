{{ config(materialized='table') }}

-- Per-neighborhood request counts for the choropleth, one layer per request
-- type: every (request_type, neighborhood polygon) pair, with its boundary ring
-- (WGS84) and the number of requests inside it (0 where none). hood_name is
-- assigned at build time by point-in-polygon, so this is a plain GROUP BY.

with counts as (
    select request_type, hood_name as name, count(*) as n
    from {{ ref('stg_service_requests') }}
    where hood_name is not null
    group by 1, 2
),

types as (
    select distinct request_type from {{ ref('stg_service_requests') }}
)

select
    t.request_type,
    nb.name          as neighborhood,
    nb.boundary_json,
    coalesce(c.n, 0) as n
from types t
cross join {{ ref('stg_neighborhoods') }} nb
left join counts c on c.request_type = t.request_type and c.name = nb.name
