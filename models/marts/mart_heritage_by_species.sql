{{ config(materialized='table') }}

-- Most-designated heritage-tree species, with average trunk diameter.

select
    common_name,
    count(*)                       as tree_count,
    round(avg(diameter_in), 1)     as avg_diameter_in
from {{ ref('stg_heritage_trees') }}
group by common_name
order by tree_count desc
