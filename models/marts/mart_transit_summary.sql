{{ config(materialized='table') }}

-- Single-row headline summary for the Overview tile and page KPIs.

select
    (select count(*) from {{ ref('stg_transit_routes') }})            as total_routes,
    (select count(*) from {{ ref('stg_transit_stops') }})             as total_stops,
    (select count(distinct mode) from {{ ref('stg_transit_routes') }}) as total_modes
