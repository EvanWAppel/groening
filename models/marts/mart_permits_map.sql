{{ config(materialized='table') }}

-- Geocoded permits for the PyDeck map: one row per permit that has WGS84
-- coordinates, carrying just the fields the map layer + tooltip need.

with permits as (
    select * from {{ ref('stg_building_permits') }}
    where longitude is not null
      and latitude is not null
      -- Guard against the ArcGIS 0/0 "no geometry" sentinel.
      and longitude between -124 and -122
      and latitude between 45 and 46
)

select
    permit_number,
    work_class,
    structure_type,
    neighborhood,
    valuation,
    new_units,
    issue_date,
    address,
    longitude,
    latitude
from permits
