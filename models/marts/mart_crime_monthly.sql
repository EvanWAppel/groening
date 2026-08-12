{{ config(materialized='table') }}

-- Monthly reported-crime volume by crime-against category.

select
    date_trunc('month', reported_date) as month,
    crime_against,
    count(*)                           as offense_count
from {{ ref('stg_crime') }}
group by 1, 2
order by 1, 2
