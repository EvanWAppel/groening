{{ config(materialized='table') }}

-- Individual heritage trees as WGS84 points for the map (sized by diameter).

select
    tree_id,
    common_name,
    neighborhood,
    diameter_in,
    longitude,
    latitude
from {{ ref('stg_heritage_trees') }}
where longitude is not null and latitude is not null
