{{ config(materialized='table') }}

-- When crime is reported: hour-of-day × weekday heatmap.

select
    reported_weekday,
    reported_hour,
    count(*) as offense_count
from {{ ref('stg_crime') }}
group by 1, 2
order by 2
