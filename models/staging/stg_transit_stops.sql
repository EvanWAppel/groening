-- TriMet GTFS stops: cast coordinates and keep only boardable stops (location_type
-- 0 or blank); stations (1) and entrances (2) are not stops to map.

with source as (
    select * from {{ source('raw', 'transit_stops') }}
)

select
    stop_id,
    stop_name,
    try_cast(stop_lat as double) as latitude,
    try_cast(stop_lon as double) as longitude,
    coalesce(try_cast(location_type as integer), 0) as location_type
from source
where coalesce(try_cast(location_type as integer), 0) = 0
    and try_cast(stop_lat as double) is not null
    and try_cast(stop_lon as double) is not null
