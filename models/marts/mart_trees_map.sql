{{ config(materialized='table') }}

-- Geocoded trees for the PyDeck density map.

select
    common_name,
    dbh_in,
    condition,
    longitude,
    latitude
from {{ ref('stg_trees') }}
where longitude is not null
  and latitude is not null
  and longitude between -124 and -122
  and latitude between 45 and 46
