-- Portland Accessory Short-Term Rental permits. Normalize the inconsistent
-- permit-type casing ("Type A" vs "TYPE B") to title case.

with source as (
    select * from {{ source('raw', 'short_term_rentals') }}
)

select
    application_number,
    address,
    -- DuckDB has no initcap; the only casing inconsistency is "TYPE B" vs "Type A".
    case
        when lower(permit_type) like 'type a%' then 'Type A'
        when lower(permit_type) like 'type b%' then 'Type B'
        else coalesce(permit_type, 'Other')
    end                                  as permit_type,
    permit_status,
    try_cast(issued_date as date)        as issued_date,
    try_cast(longitude as double)        as longitude,
    try_cast(latitude as double)         as latitude
from source
