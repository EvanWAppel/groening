-- PortlandMaps residential building permits (point geometry, with valuation).
-- fetch_layer normalizes the esri date fields (INDATE/ISSUEDATE) to
-- "YYYY-MM-DD HH:MM:SS" strings, so cast them to date here.

with source as (
    select * from {{ source('raw', 'building_permits') }}
)

select
    "FOLDERNUMB"                             as permit_number,
    "STATUS"                                 as status,
    "NEWCLASS"                               as work_class,
    "NEWTYPE"                                as structure_type,
    "WORKDESC"                               as work_description,
    "FOLDER_DES"                             as folder_description,
    "NBRHOOD"                                as neighborhood,
    "IS_ADU"                                 as is_adu,
    try_cast("VALUATION" as double)          as valuation,
    try_cast("NEW_UNITS" as double)          as new_units,
    try_cast("SQFT" as integer)              as sqft,
    try_cast("YEAR_" as integer)             as permit_year,
    try_cast("ISSUEDATE" as timestamp)::date as issue_date,
    try_cast("INDATE" as timestamp)::date    as intake_date,
    "PROP_ADDRE"                             as address,
    try_cast(longitude as double)            as longitude,
    try_cast(latitude as double)             as latitude
from source
