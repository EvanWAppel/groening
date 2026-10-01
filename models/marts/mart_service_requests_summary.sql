{{ config(materialized='table') }}

-- One headline row per request type: volume, open/closed split, and coverage.

select
    request_type,
    count(*)                                        as total_requests,
    count(*) filter (where status = 'Open')         as open_requests,
    count(*) filter (where status = 'Closed')       as closed_requests,
    min(created_date)                               as first_date,
    max(created_date)                               as last_date
from {{ ref('stg_service_requests') }}
group by 1
order by 1
