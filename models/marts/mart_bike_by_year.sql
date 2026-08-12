{{ config(materialized='table') }}

-- Bike-facility miles built per year + cumulative network growth (active,
-- currently-built segments with a real build year).

with built as (
    select * from {{ ref('stg_bike_network') }}
    where year_built between 1970 and year(current_date)
      and year_retired is null
      and length_miles is not null
),

per_year as (
    select
        year_built,
        round(sum(length_miles), 1) as miles_built,
        count(*)                    as segments
    from built
    group by 1
)

select
    year_built,
    miles_built,
    segments,
    round(sum(miles_built) over (order by year_built), 1) as cumulative_miles
from per_year
order by year_built
