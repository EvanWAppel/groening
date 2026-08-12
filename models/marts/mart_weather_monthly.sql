{{ config(materialized='table') }}

-- Calendar-month climatology across all years: the classic Portland wet-season
-- curve plus typical temperatures.

with days as (
    select * from {{ ref('stg_weather') }}
)

select
    extract('month' from obs_date)               as month_num,
    monthname(obs_date)                          as month_name,
    round(avg(precip_in), 3)                     as avg_precip_in,
    round(avg(case when precip_in > 0.01 then 1.0 else 0.0 end), 3) as rainy_day_frac,
    round(avg(tmax_f), 1)                        as avg_tmax_f,
    round(avg(tmin_f), 1)                        as avg_tmin_f
from days
group by 1, 2
order by 1
