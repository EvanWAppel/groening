{{ config(materialized='table') }}

-- Most common species with average size and native flag.

select
    coalesce(common_name, 'Unknown') as common_name,
    genus,
    max(native)          as native,
    count(*)             as tree_count,
    round(avg(dbh_in), 1) as avg_dbh_in
from {{ ref('stg_trees') }}
group by 1, 2
order by tree_count desc
