{{ config(materialized='table') }}

-- Service frequency: scheduled trips per route on one reference weekday,
-- Saturday and Sunday.
--
-- A GTFS feed carries several overlapping service periods (this week's
-- schedule, next month's service change, past weeks still in the file), so
-- summing every trip per route would double count. Instead we pick one concrete
-- date per day type and count only trips whose service_id runs on it
-- (calendar.txt: day flag set and date within [start_date, end_date]).
--
-- Reference dates: the first Wednesday (a mid-week weekday, clear of Monday and
-- Friday holiday patterns), Saturday and Sunday on/after the warehouse build
-- date — clamped into the feed's own date range so a stale build still lands on
-- a week the feed covers. calendar_dates.txt exceptions are not applied.

with anchor as (
    select
        least(
            greatest(
                (select max(built_at)::date from {{ ref('stg_build_metadata') }}),
                (select min(start_date) from {{ ref('stg_transit_calendar') }})
            ),
            (select max(end_date) from {{ ref('stg_transit_calendar') }}) - 6
        ) as d
),

-- dayofweek: 0 = Sunday ... 6 = Saturday. Next date with that weekday on/after d.
ref_dates as (
    select
        d + cast((3 - dayofweek(d) + 7) % 7 as integer) as weekday_date,
        d + cast((6 - dayofweek(d) + 7) % 7 as integer) as saturday_date,
        d + cast((0 - dayofweek(d) + 7) % 7 as integer) as sunday_date
    from anchor
),

active as (
    select
        c.service_id,
        (c.wednesday and r.weekday_date between c.start_date and c.end_date)  as on_weekday,
        (c.saturday and r.saturday_date between c.start_date and c.end_date)  as on_saturday,
        (c.sunday and r.sunday_date between c.start_date and c.end_date)      as on_sunday
    from {{ ref('stg_transit_calendar') }} as c
    cross join ref_dates as r
),

per_route as (
    select
        t.route_id,
        count(*) filter (where a.on_weekday)  as weekday_trips,
        count(*) filter (where a.on_saturday) as saturday_trips,
        count(*) filter (where a.on_sunday)   as sunday_trips
    from {{ ref('stg_transit_trips') }} as t
    inner join active as a on t.service_id = a.service_id
    group by t.route_id
)

select
    rt.route_id,
    rt.route_short_name,
    rt.route_long_name,
    rt.mode,
    rt.route_color,
    coalesce(p.weekday_trips, 0)::integer  as weekday_trips,
    coalesce(p.saturday_trips, 0)::integer as saturday_trips,
    coalesce(p.sunday_trips, 0)::integer   as sunday_trips,
    r.weekday_date,
    r.saturday_date,
    r.sunday_date
from {{ ref('stg_transit_routes') }} as rt
left join per_route as p on rt.route_id = p.route_id
cross join ref_dates as r
order by weekday_trips desc, rt.route_short_name
