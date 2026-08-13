{{ config(materialized='table') }}

-- The most recent inspection per establishment (permit) — the "current scores"
-- table that anchors the page. One row per food facility.

with ranked as (
    select
        *,
        row_number() over (
            partition by permit_id
            order by inspection_date desc, inspection_id
        ) as rn
    from {{ ref('stg_restaurant_inspections') }}
)

select
    establishment_name,
    address,
    city,
    zip,
    inspection_type,
    permit_type,
    purpose,
    inspection_date,
    sanitation_score
from ranked
where rn = 1
order by inspection_date desc, establishment_name
