{{ config(materialized='table') }}

-- Short-term-rental permit roster for the map, table, and page-side breakdowns.

with str as (
    select * from {{ ref('stg_short_term_rentals') }}
)

select
    application_number,
    address,
    coalesce(permit_type, 'Unknown')   as permit_type,
    coalesce(permit_status, 'Unknown') as permit_status,
    issued_date,
    longitude,
    latitude,
    (longitude between -124 and -122 and latitude between 45 and 46) as has_valid_point
from str
