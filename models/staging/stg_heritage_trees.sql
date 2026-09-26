-- City-designated heritage trees. Keep only ACTIVE designations (no Delist_Date);
-- normalize species, size, designation year, and the native flag.

with source as (
    select * from {{ source('raw', 'heritage_trees') }}
)

select
    try_cast(treeid as integer)                          as tree_id,
    coalesce(nullif(trim(common), ''), 'Unknown')        as common_name,
    scientific                                           as scientific_name,
    try_cast(height as integer)                          as height_ft,
    try_cast(diameter as integer)                        as diameter_in,
    try_cast(circumf as double)                          as circumference_in,
    try_cast(year_designated as integer)                 as year_designated,
    neighborhood,
    case
        when native = 'Yes' then true
        when native = 'No' then false
    end                                                  as native,
    longitude,
    latitude
from source
where delist_date is null   -- active heritage-tree designations only
