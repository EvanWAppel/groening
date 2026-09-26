{{ config(materialized='table') }}

-- Resources by architectural style.

select
    style,
    count(*) as resources
from {{ ref('stg_historic') }}
group by style
order by resources desc
