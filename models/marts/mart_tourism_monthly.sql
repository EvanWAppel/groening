{{ config(materialized='table') }}

-- Monthly international passengers — shows the 2020 COVID collapse + recovery.

select
    month_date,
    year,
    month,
    passengers
from {{ ref('stg_tourism') }}
where passengers is not null
order by month_date
