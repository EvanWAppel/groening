-- TriMet GTFS calendar: one row per service pattern, with the weekdays it runs
-- (0/1 flags -> booleans) and its inclusive YYYYMMDD date range (-> date).
-- calendar_dates.txt (holiday add/remove exceptions) is not loaded: the
-- frequency mart describes the regular schedule, not a specific holiday.

with source as (
    select * from {{ source('raw', 'transit_calendar') }}
)

select
    service_id,
    monday = '1'    as monday,
    tuesday = '1'   as tuesday,
    wednesday = '1' as wednesday,
    thursday = '1'  as thursday,
    friday = '1'    as friday,
    saturday = '1'  as saturday,
    sunday = '1'    as sunday,
    try_strptime(start_date, '%Y%m%d')::date as start_date,
    try_strptime(end_date, '%Y%m%d')::date   as end_date
from source
