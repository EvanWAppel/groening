-- USGS daily mean discharge for the Willamette at Portland.

with source as (
    select * from {{ source('raw', 'willamette') }}
)

select
    try_cast(date as date)          as obs_date,
    try_cast(discharge_cfs as double) as discharge_cfs,
    cast(provisional as boolean)    as provisional
from source
