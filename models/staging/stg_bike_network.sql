-- PBOT bicycle network segments. YearBuilt/LengthMiles drive the growth story.

with source as (
    select * from {{ source('raw', 'bike_network') }}
)

select
    "SegmentName"                  as segment_name,
    "Status"                       as status,
    "Facility"                     as facility,
    try_cast("YearBuilt" as integer)  as year_built,
    try_cast("YearRetired" as integer) as year_retired,
    try_cast("LengthMiles" as double)  as length_miles
from source
