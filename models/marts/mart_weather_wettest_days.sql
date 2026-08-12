{{ config(materialized='table') }}

-- The rainiest single days on record — Portland's "atmospheric river" hall of fame.

with days as (
    select * from {{ ref('stg_weather') }}
    where precip_in is not null
)

select
    obs_date,
    round(precip_in, 2) as precip_in
from days
order by precip_in desc
limit 25
