-- BTS international passengers for PDX, monthly.

with source as (
    select * from {{ source('raw', 'tourism') }}
)

select
    try_cast(year as integer)                                    as year,
    try_cast(month as integer)                                   as month,
    make_date(try_cast(year as integer), try_cast(month as integer), 1) as month_date,
    try_cast(sum_total as bigint)                                as passengers
from source
