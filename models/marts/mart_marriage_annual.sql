{{ config(materialized='table') }}

-- Multnomah marriages per year with the same-sex share (Oregon legalized
-- same-sex marriage in May 2014 — a visible spike).

select
    year,
    total,
    same_sex,
    case when total > 0 then round(100.0 * same_sex / total, 1) end as same_sex_pct,
    preliminary
from {{ ref('stg_marriage') }}
where total is not null
order by year
