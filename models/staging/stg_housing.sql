-- Portland Housing Bureau regulated affordable-housing portfolio: normalize types
-- and keep the project attributes the page needs. DuckDB matches column names
-- case-insensitively, so the raw MixedCase columns resolve here.

with source as (
    select * from {{ source('raw', 'housing') }}
)

select
    try_cast(objectid as integer)         as project_id,
    project_name,
    sponsor_name,
    property_address,
    try_cast(total_unit as integer)       as total_units,
    try_cast(regulated_units as integer)  as regulated_units,
    coalesce(nullif(trim(building_type), ''), 'Unspecified') as building_type,
    analysis_area,
    ura,
    try_cast(year_complet as integer)     as year_completed,
    longitude,
    latitude
from source
