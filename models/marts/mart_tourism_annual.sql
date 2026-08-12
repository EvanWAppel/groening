{{ config(materialized='table') }}

-- Annual international passengers (drop partial current year at the page level).

select
    year,
    sum(passengers)  as passengers,
    count(*)         as months_reported
from {{ ref('stg_tourism') }}
where passengers is not null
group by 1
order by 1
