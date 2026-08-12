-- Multnomah County marriages (aggregate yearly counts) from Oregon OHA.

with source as (
    select * from {{ source('raw', 'marriage') }}
)

select
    try_cast(year as integer)       as year,
    try_cast(total as integer)      as total,
    try_cast(same_sex as integer)   as same_sex,
    cast(preliminary as boolean)    as preliminary
from source
