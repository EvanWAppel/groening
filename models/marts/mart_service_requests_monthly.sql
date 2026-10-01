{{ config(materialized='table') }}

-- Monthly request volume by request type.

select
    date_trunc('month', created_date) as month,
    request_type,
    count(*)                          as request_count
from {{ ref('stg_service_requests') }}
group by 1, 2
order by 1, 2
