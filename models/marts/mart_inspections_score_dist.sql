{{ config(materialized='table') }}

-- Distribution of sanitation scores across all scored food inspections in the
-- window, bucketed into bands (scores cluster in the 90s, so the top bands are
-- narrow). `band_order` drives a left-to-right worst->best axis in the chart.

with scored as (
    select sanitation_score as s
    from {{ ref('stg_restaurant_inspections') }}
    where sanitation_score is not null
)

select
    case
        when s = 100 then '100'
        when s >= 95 then '95-99'
        when s >= 90 then '90-94'
        when s >= 80 then '80-89'
        when s >= 70 then '70-79'
        else '< 70'
    end as score_band,
    case
        when s = 100 then 6
        when s >= 95 then 5
        when s >= 90 then 4
        when s >= 80 then 3
        when s >= 70 then 2
        else 1
    end as band_order,
    count(*) as inspections
from scored
group by 1, 2
order by band_order
