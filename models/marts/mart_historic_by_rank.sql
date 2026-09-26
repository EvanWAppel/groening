{{ config(materialized='table') }}

-- Resources by significance rank (I / II / III / designated / unranked).

select
    significance_rank,
    count(*) as resources
from {{ ref('stg_historic') }}
group by significance_rank
order by resources desc
