-- Metro Urban Growth Boundary: one row with area and the outer-ring geometry.

with source as (
    select * from {{ source('raw', 'ugb') }}
)

select
    try_cast(area_sqft as double)            as area_sqft,
    try_cast(area_sqft as double) / 27878400 as area_sqmi,
    boundary_json
from source
