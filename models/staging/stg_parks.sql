-- PortlandMaps park boundaries. Geometry is a polygon; fetch_parks attaches a
-- WGS84 centroid (longitude/latitude) so the app can map parks as points.

with source as (
    select * from {{ source('raw', 'parks') }}
)

select
    try_cast("PROPERTYID" as bigint) as property_id,
    "NAME"                           as name,
    try_cast("ACRES" as double)      as acres,
    try_cast(longitude as double)    as longitude,
    try_cast(latitude as double)     as latitude
from source
