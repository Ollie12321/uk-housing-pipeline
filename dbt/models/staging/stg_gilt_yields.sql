with source as (
    select * from {{ source('raw', 'gilt_yields') }}
),

deduplicated as (
    select
        date,
        yield_pct,
        ticker,
        loaded_at,
        row_number() over (
            partition by date
            order by loaded_at desc
        ) as rn
    from source
    where date is not null
),

final as (
    select
        date,
        yield_pct,
        ticker,
        loaded_at
    from deduplicated
    where rn = 1
)

select * from final
