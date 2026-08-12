{{ config(materialized='table') }}

-- Monthly mean / range discharge — smooths the daily series for the trend view.

with daily as (
    select * from {{ ref('stg_willamette') }}
    where discharge_cfs is not null
)

select
    date_trunc('month', obs_date) as month,
    round(avg(discharge_cfs), 0)  as avg_cfs,
    min(discharge_cfs)            as min_cfs,
    max(discharge_cfs)            as max_cfs
from daily
group by 1
order by 1
