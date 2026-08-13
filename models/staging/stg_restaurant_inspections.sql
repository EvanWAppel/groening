-- Multnomah County food-facility inspections (restaurants, carts, warehouses)
-- from the MyHealthDepartment searchInspections API. Non-food programs
-- (pools/spas/lodging) come back in the same feed and are filtered out here.
-- Food restaurants/carts carry a 0-100 sanitation score; a 0 means "non-scored"
-- (e.g. a warehouse), so it is surfaced as a NULL sanitation_score.

with source as (
    select * from {{ source('raw', 'restaurant_inspections') }}
)

select
    "inspectionID"                                as inspection_id,
    "permitID"                                    as permit_id,
    "establishmentName"                           as establishment_name,
    trim("addressLine1" || ' ' || coalesce("addressLine2", ''))  as address,
    city,
    zip,
    "inspectionType"                              as inspection_type,
    purpose,
    "permitType"                                  as permit_type,
    cast(substr("inspectionDate", 1, 10) as date) as inspection_date,
    try_cast(score as integer)                    as score,
    case when try_cast(score as integer) > 0 then try_cast(score as integer) end
                                                  as sanitation_score
from source
where "programName" = 'Food'
