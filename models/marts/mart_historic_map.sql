{{ config(materialized='table') }}

-- Historic resources as WGS84 points for the density map.

select
    orig_name,
    style,
    significance_rank,
    longitude,
    latitude
from {{ ref('stg_historic') }}
where longitude is not null and latitude is not null
