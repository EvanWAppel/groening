{{ config(materialized='table') }}

-- Single-row headline summary for the Overview tile and page KPIs.

select
    count(*)                                         as total_resources,
    count(distinct style)                            as style_count,
    min(year_built)                                  as oldest_year,
    count(*) filter (where significance_rank in ('I', 'II', 'designated')) as significant_count
from {{ ref('stg_historic') }}
