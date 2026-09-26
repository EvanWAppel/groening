{{ config(materialized='table') }}

-- Resources by decade built (parsed, in-range years only).

select
    (year_built // 10) * 10 as decade,
    count(*)                as resources
from {{ ref('stg_historic') }}
where year_built is not null
group by decade
order by decade
