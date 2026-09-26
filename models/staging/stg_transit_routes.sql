-- TriMet GTFS routes: normalize types and map the GTFS route_type enum to a
-- human mode label. route_type values per the GTFS spec (TriMet uses 0/2/3/5).

with source as (
    select * from {{ source('raw', 'transit_routes') }}
)

select
    route_id,
    route_short_name,
    route_long_name,
    try_cast(route_type as integer) as route_type,
    case try_cast(route_type as integer)
        when 0 then 'MAX Light Rail'
        when 1 then 'Subway'
        when 2 then 'WES Commuter Rail'
        when 3 then 'Bus'
        when 4 then 'Ferry'
        when 5 then 'Streetcar'
        when 6 then 'Aerial Tram'
        when 7 then 'Funicular'
        else 'Other'
    end as mode,
    route_color
from source
