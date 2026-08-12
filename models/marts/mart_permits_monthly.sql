{{ config(materialized='table') }}

-- Permit volume, valuation, and new units per month — the building-cycle series.

with permits as (
    select * from {{ ref('stg_building_permits') }}
    where issue_date is not null
)

select
    date_trunc('month', issue_date) as issue_month,
    count(*)                        as permit_count,
    sum(valuation)                  as total_valuation,
    round(avg(valuation), 0)        as avg_valuation,
    sum(new_units)                  as total_new_units
from permits
group by 1
order by 1
