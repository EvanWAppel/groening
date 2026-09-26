{{ config(materialized='table') }}

-- Route count per mode (Bus, MAX Light Rail, WES Commuter Rail, Streetcar, ...).

select
    mode,
    count(*) as route_count
from {{ ref('stg_transit_routes') }}
group by mode
order by route_count desc
