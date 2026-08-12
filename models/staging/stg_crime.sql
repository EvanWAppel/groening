-- PPB reported crime (rolling 12-month window). REPORTED_DATETIME is normalized
-- to a "YYYY-MM-DD HH:MM:SS" string by fetch_layer; cast to timestamp and derive
-- hour / weekday for the time-pattern heatmap. Drop future-dated dirty rows.

with source as (
    select * from {{ source('raw', 'crime') }}
),

typed as (
    select
        try_cast("REPORTED_DATETIME" as timestamp) as reported_at,
        "CategoryName"               as crime_against,
        "OffenseGroupDescription"    as offense_group,
        "CrimeType"                  as crime_type,
        try_cast(longitude as double) as longitude,
        try_cast(latitude as double)  as latitude
    from source
)

select
    reported_at,
    reported_at::date        as reported_date,
    extract('hour' from reported_at)  as reported_hour,
    dayname(reported_at)              as reported_weekday,
    crime_against,
    offense_group,
    crime_type,
    longitude,
    latitude
from typed
where reported_at is not null
  and reported_at <= now()
