with source as (
    select * from {{ source('raw', 'boe_rate_events_streaming') }}
),

deduplicated as (
    select
        event_id,
        effective_date,
        previous_rate,
        new_rate,
        published_at,
        row_number() over (
            partition by event_id
            order by published_at desc
        ) as rn
    from source
    where event_id is not null
        and new_rate is not null
),

final as (
    select
        event_id,
        effective_date,
        previous_rate,
        new_rate,
        published_at
    from deduplicated
    where rn = 1
)

select * from final
