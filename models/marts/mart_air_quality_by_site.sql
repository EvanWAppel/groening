{{ config(materialized='table') }}

-- Per-site, per-pollutant summary for the monitor map and site table.

with aq as (
    select * from {{ ref('stg_air_quality') }}
    where aqi is not null
      and longitude is not null
      and latitude is not null
)

select
    county,
    site_name,
    pollutant,
    round(avg(aqi), 1)  as avg_aqi,
    max(aqi)            as max_aqi,
    count(*)            as observations,
    avg(longitude)      as longitude,
    avg(latitude)       as latitude
from aq
group by 1, 2, 3
order by county, site_name
