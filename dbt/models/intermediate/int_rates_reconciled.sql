{{
    config(
        materialized='view',
        description='Unified BoE base rate series — batch and streaming combined and deduplicated.'
    )
}}

/*
  Unions the daily batch rates (stg_boe_rates) with real-time streaming
  events (stg_boe_rate_events_streaming).

  When the rate changes intra-day, the streaming table has it immediately;
  the batch table catches up overnight. Deduplication on effective_date
  ensures downstream models see a single consistent rate per day.

  Priority: streaming > batch (streaming events are considered more timely).
*/

with batch as (
    select
        effective_date,
        base_rate,
        'batch' as source_type
    from {{ ref('stg_boe_rates') }}
),

streaming as (
    select
        effective_date,
        new_rate as base_rate,
        'streaming' as source_type
    from {{ ref('stg_boe_rate_events_streaming') }}
),

combined as (
    select * from batch
    union all
    select * from streaming
),

deduplicated as (
    select
        effective_date,
        base_rate,
        source_type,
        row_number() over (
            partition by effective_date
            -- streaming rows win when both exist for same date
            order by case source_type when 'streaming' then 1 else 2 end
        ) as rn
    from combined
),

final as (
    select
        effective_date,
        base_rate,
        source_type,
        -- Carry the rate forward to fill month gaps (rates don't change daily)
        date_trunc(effective_date, month) as effective_month
    from deduplicated
    where rn = 1
)

select * from final
