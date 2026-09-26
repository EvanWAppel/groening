{{ config(materialized='table') }}

-- Projects and regulated units by building type.

select
    building_type,
    count(*)              as projects,
    sum(regulated_units)  as regulated_units
from {{ ref('stg_housing') }}
group by building_type
order by projects desc
