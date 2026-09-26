{{ config(materialized='table') }}

-- One row per transit route, with its mode label and display color.

select
    route_id,
    route_short_name,
    route_long_name,
    mode,
    route_color
from {{ ref('stg_transit_routes') }}
order by mode, route_short_name
