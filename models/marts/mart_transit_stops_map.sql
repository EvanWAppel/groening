{{ config(materialized='table') }}

-- Boardable stops with WGS84 coordinates for the PyDeck hexbin map.

select
    stop_id,
    stop_name,
    longitude,
    latitude
from {{ ref('stg_transit_stops') }}
