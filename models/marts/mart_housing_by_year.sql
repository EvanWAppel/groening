{{ config(materialized='table') }}

-- Regulated affordable units completed per year (the affordable-housing pipeline).

select
    year_completed        as year,
    count(*)              as projects,
    sum(regulated_units)  as regulated_units
from {{ ref('stg_housing') }}
where year_completed is not null and year_completed > 1900
group by year_completed
order by year_completed
