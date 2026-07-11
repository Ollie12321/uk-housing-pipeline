with source as (
    select * from {{ source('raw', 'boe_base_rates') }}
),

deduplicated as (
    select
        effective_date,
        base_rate,
        source,
        loaded_at,
        row_number() over (
            partition by effective_date
            order by loaded_at desc
        ) as rn
    from source
    where base_rate between 0 and 20
        and effective_date is not null
),

final as (
    select
        effective_date,
        base_rate,
        source,
        loaded_at
    from deduplicated
    where rn = 1
)

select * from final
