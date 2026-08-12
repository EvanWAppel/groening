{{ config(materialized='table') }}

-- Pass-through of the single UGB polygon for the boundary map + area stat.

select
    round(area_sqmi, 1) as area_sqmi,
    boundary_json
from {{ ref('stg_ugb') }}
