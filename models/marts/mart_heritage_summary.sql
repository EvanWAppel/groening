{{ config(materialized='table') }}

-- Single-row headline summary for the Overview tile and page KPIs.

select
    count(*)                                as total_trees,
    count(distinct common_name)             as species_count,
    min(year_designated)                    as first_year,
    max(diameter_in)                        as max_diameter_in,
    round(100.0 * count(*) filter (where native) / nullif(count(*) filter (where native is not null), 0), 0) as native_pct
from {{ ref('stg_heritage_trees') }}
