-- TriMet GTFS trips: one row per scheduled trip. service_id links to the
-- service calendar (which days/dates the trip runs); ids stay strings.

with source as (
    select * from {{ source('raw', 'transit_trips') }}
)

select
    trip_id,
    route_id,
    service_id,
    try_cast(direction_id as integer) as direction_id
from source
