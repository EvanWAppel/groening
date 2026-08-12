-- NOAA GHCN-Daily for PDX. Convert the tenths-unit integers to US-friendly
-- physical units (°F, inches) here; drop the sparse pre-1938 head where temps
-- and precip are blank.

with source as (
    select * from {{ source('raw', 'weather') }}
)

select
    try_cast("DATE" as date)                    as obs_date,
    try_cast("TMAX" as double) / 10.0 * 9 / 5 + 32 as tmax_f,
    try_cast("TMIN" as double) / 10.0 * 9 / 5 + 32 as tmin_f,
    try_cast("PRCP" as double) / 10.0 / 25.4     as precip_in,
    try_cast("SNOW" as double) / 25.4            as snow_in,
    try_cast("SNWD" as double) / 25.4            as snow_depth_in
from source
where try_cast("DATE" as date) >= date '1938-04-01'
