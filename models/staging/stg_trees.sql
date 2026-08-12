-- PortlandMaps Parks Tree Inventory. Use Common_name/Genus_species for display
-- (Species is a code); carry the ecosystem-benefit metrics.

with source as (
    select * from {{ source('raw', 'trees') }}
)

select
    "Common_name"                          as common_name,
    "Genus"                                as genus,
    "Genus_species"                        as species,
    "Family"                               as family,
    "Native"                               as native,
    "Condition"                            as condition,
    try_cast("DBH" as double)              as dbh_in,
    try_cast("TreeHeight" as double)       as height_ft,
    try_cast("Carbon_Storage_lb" as double) as carbon_storage_lb,
    try_cast("Stormwater_ft" as double)    as stormwater_cf,
    try_cast("Total_Annual_Benefits" as double) as annual_benefits_usd,
    try_cast(longitude as double)          as longitude,
    try_cast(latitude as double)           as latitude
from source
