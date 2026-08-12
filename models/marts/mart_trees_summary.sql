{{ config(materialized='table') }}

-- One-row headline summary of the inventoried tree collection.

select
    count(*)                              as total_trees,
    count(distinct common_name)           as species_count,
    round(sum(carbon_storage_lb) / 2000, 0) as carbon_storage_tons,
    round(sum(annual_benefits_usd), 0)    as annual_benefits_usd,
    round(avg(dbh_in), 1)                 as avg_dbh_in
from {{ ref('stg_trees') }}
