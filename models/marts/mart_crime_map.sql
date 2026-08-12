{{ config(materialized='table') }}

-- Geocoded offenses for the PyDeck hexbin density map.

select
    crime_against,
    offense_group,
    reported_date,
    longitude,
    latitude
from {{ ref('stg_crime') }}
where longitude is not null
  and latitude is not null
  and longitude between -124 and -122
  and latitude between 45 and 46
