{{ config(materialized='table') }}

-- Count of unhealthy-air days per year (any site AQI > 100), by pollutant —
-- captures wildfire-smoke summers, a real Portland air-quality story.

with aq as (
    select * from {{ ref('stg_air_quality') }}
    where aqi is not null
),

daily_max as (
    select
        obs_date,
        pollutant,
        max(aqi) as worst_aqi
    from aq
    group by 1, 2
)

select
    extract('year' from obs_date) as year,
    pollutant,
    count(*) filter (where worst_aqi > 100) as unhealthy_days
from daily_max
group by 1, 2
order by 1, 2
