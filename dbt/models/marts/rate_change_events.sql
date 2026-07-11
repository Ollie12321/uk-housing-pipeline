{{
    config(
        materialized='table',
        description='One row per BoE rate change event, with direction and magnitude.'
    )
}}

with rates as (
    select
        effective_date,
        effective_month,
        base_rate,
        source_type,
        lag(base_rate) over (order by effective_date) as previous_rate
    from {{ ref('int_rates_reconciled') }}
),

changes as (
    select
        effective_date,
        effective_month,
        base_rate,
        previous_rate,
        base_rate - previous_rate                  as rate_change_bps,
        case
            when base_rate > previous_rate then 'hike'
            when base_rate < previous_rate then 'cut'
            else 'hold'
        end                                        as direction,
        source_type
    from rates
    where previous_rate is not null
        and base_rate != previous_rate
)

select * from changes
order by effective_date
