-- EPA AQS daily PM2.5 / Ozone for the OR tri-county metro. Coordinates are
-- already WGS84. Shorten the verbose parameter names to a clean label.

with source as (
    select * from {{ source('raw', 'air_quality') }}
)

select
    "County Name"                        as county,
    "Site Num"                           as site_num,
    "Local Site Name"                    as site_name,
    try_cast("Date Local" as date)       as obs_date,
    case
        when "Parameter Name" ilike '%PM2.5%' then 'PM2.5'
        when "Parameter Name" ilike '%Ozone%' then 'Ozone'
        else "Parameter Name"
    end                                  as pollutant,
    try_cast("Arithmetic Mean" as double) as concentration,
    "Units of Measure"                   as units,
    try_cast("AQI" as integer)           as aqi,
    try_cast("Latitude" as double)       as latitude,
    try_cast("Longitude" as double)      as longitude
from source
