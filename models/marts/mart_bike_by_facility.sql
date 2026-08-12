{{ config(materialized='table') }}

-- Current active network mileage by facility type.

select
    coalesce(facility, 'Unknown') as facility,
    round(sum(length_miles), 1)   as miles,
    count(*)                      as segments
from {{ ref('stg_bike_network') }}
where year_retired is null
  and length_miles is not null
group by 1
order by miles desc
