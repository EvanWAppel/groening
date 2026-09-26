{{ config(materialized='table') }}

-- Single-row headline summary for the Overview tile and page KPIs.

select
    count(*)              as total_projects,
    sum(total_units)      as total_units,
    sum(regulated_units)  as regulated_units
from {{ ref('stg_housing') }}
