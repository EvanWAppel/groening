{{ config(materialized='table') }}

-- Full daily discharge series for the signature line chart.

select
    obs_date,
    discharge_cfs,
    provisional
from {{ ref('stg_willamette') }}
where discharge_cfs is not null
order by obs_date
