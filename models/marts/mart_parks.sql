{{ config(materialized='table') }}

-- Viz-ready parks: name, acreage, a size class for the distribution chart, and a
-- WGS84 centroid for the map (guarded to the Portland-metro bounding box).

with parks as (
    select * from {{ ref('stg_parks') }}
    where name is not null
)

select
    name,
    acres,
    case
        when acres < 1  then '1 · Pocket (<1 ac)'
        when acres < 10 then '2 · Small (1–10 ac)'
        when acres < 50 then '3 · Medium (10–50 ac)'
        else                 '4 · Large (50+ ac)'
    end as size_class,
    longitude,
    latitude,
    (longitude between -124 and -122 and latitude between 45 and 46) as has_valid_point
from parks
order by acres desc
