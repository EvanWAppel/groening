{{ config(materialized='table') }}

-- Monthly average / peak AQI per pollutant across the tri-county metro.

with aq as (
    select * from {{ ref('stg_air_quality') }}
    where aqi is not null
)

select
    date_trunc('month', obs_date) as month,
    pollutant,
    round(avg(aqi), 1)            as avg_aqi,
    max(aqi)                      as max_aqi
from aq
group by 1, 2
order by 1, 2
