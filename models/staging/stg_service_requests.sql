-- Unified service requests (graffiti + potholes). created_at is normalized to a
-- "YYYY-MM-DD HH:MM:SS" string by fetch_layer; cast to timestamp and drop
-- undated / future-dated rows. Graffiti's free-text Graffiti_Status is bucketed
-- into a handful of resolution outcomes for the page (potholes carry none).

with source as (
    select * from {{ source('raw', 'service_requests') }}
),

typed as (
    select
        request_type,
        request_id,
        status,
        raw_status,
        resolution                          as resolution_detail,
        try_cast(created_at as timestamp)   as created_at,
        hood_name,
        try_cast(longitude as double)       as longitude,
        try_cast(latitude as double)        as latitude
    from source
)

select
    request_type,
    request_id,
    status,
    raw_status,
    case
        when request_type <> 'Graffiti' then null
        when resolution_detail is null then 'Not recorded'
        when lower(resolution_detail) like '%cleaned by contractor%' then 'Cleaned by contractor'
        when lower(resolution_detail) like '%cleaned by pbot%' then 'Cleaned by PBOT'
        when lower(resolution_detail) like '%cleaned by property owner%' then 'Cleaned by property owner'
        when lower(resolution_detail) like '%referred%' then 'Referred to another agency'
        when lower(resolution_detail) like 'open%'
          or lower(resolution_detail) like 'pending%' then 'Open / pending'
        when lower(resolution_detail) like '%solved%' then 'Solved (other)'
        else 'Other'
    end                                     as resolution,
    resolution_detail,
    created_at,
    created_at::date                        as created_date,
    hood_name,
    longitude,
    latitude
from typed
where created_at is not null
  and created_at <= now()
