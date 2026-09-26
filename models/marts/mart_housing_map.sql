{{ config(materialized='table') }}

-- Regulated affordable-housing projects as WGS84 points for the map.

select
    project_name,
    total_units,
    regulated_units,
    longitude,
    latitude
from {{ ref('stg_housing') }}
where longitude is not null and latitude is not null
