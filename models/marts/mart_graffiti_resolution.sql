{{ config(materialized='table') }}

-- How graffiti reports were resolved: bucketed Graffiti_Status outcomes.

select
    resolution,
    count(*) as request_count
from {{ ref('stg_service_requests') }}
where request_type = 'Graffiti'
group by 1
order by 2 desc
