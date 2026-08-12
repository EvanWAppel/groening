{{ config(materialized='table') }}

-- Offense-group counts (within the rolling 12-month window).

select
    crime_against,
    coalesce(offense_group, 'Unknown') as offense_group,
    count(*)                           as offense_count
from {{ ref('stg_crime') }}
group by 1, 2
order by offense_count desc
