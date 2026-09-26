{{ config(materialized='table') }}

-- Heritage-tree designations per year (active designations).

select
    year_designated       as year,
    count(*)              as designated
from {{ ref('stg_heritage_trees') }}
where year_designated is not null and year_designated > 1900
group by year_designated
order by year_designated
