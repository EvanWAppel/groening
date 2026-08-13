{{ config(materialized='table') }}

-- Inspection volume and average sanitation score per month across the rolling
-- window. `scored` counts only rows that carry a 0-100 score (restaurants/carts).

select
    date_trunc('month', inspection_date) as month,
    count(*)                             as inspections,
    count(sanitation_score)              as scored,
    round(avg(sanitation_score), 1)      as avg_score
from {{ ref('stg_restaurant_inspections') }}
where inspection_date is not null
group by 1
order by 1
