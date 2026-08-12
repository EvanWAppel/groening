{{ config(materialized='table') }}

-- Per-year rainfall totals, rainy-day counts, and temperature extremes.

with days as (
    select * from {{ ref('stg_weather') }}
)

select
    extract('year' from obs_date)                as year,
    round(sum(precip_in), 2)                     as total_precip_in,
    count(*) filter (where precip_in > 0.01)     as rainy_days,
    round(max(tmax_f), 1)                        as record_high_f,
    round(min(tmin_f), 1)                        as record_low_f
from days
group by 1
having count(*) > 350   -- only years with near-complete coverage
order by 1
