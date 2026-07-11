{{
    config(
        materialized='table',
        partition_by={
            'field': 'month',
            'data_type': 'date',
            'granularity': 'month'
        },
        cluster_by=['region'],
        description='The centrepiece model. Transaction volumes and prices per region/month with rate context at 0–6 month lags.'
    )
}}

/*
  Joins monthly transaction aggregates to the prevailing BoE base rate at
  0, 1, 2, 3, and 6 months prior.  The resulting rate_change_Nm columns
  let you answer "what happened to transaction volumes N months after a
  rate change?" — the core business question.
*/

with monthly_txns as (
    select * from {{ ref('monthly_transactions_by_region') }}
),

rates as (
    select
        effective_month,
        base_rate
    from {{ ref('int_rates_reconciled') }}
),

-- Expand rates to every calendar month (carry-forward between changes)
all_months as (
    select distinct month as calendar_month from monthly_txns
),

rate_at_month as (
    select
        am.calendar_month,
        array_agg(r.base_rate order by r.effective_month desc limit 1)[safe_offset(0)] as base_rate
    from all_months am
    join rates r on r.effective_month <= am.calendar_month
    group by am.calendar_month
),

lagged as (
    select
        t.month,
        t.region,
        t.property_type,
        t.transaction_count,
        t.avg_price,
        t.median_price,
        t.min_price,
        t.max_price,
        r_0.base_rate                             as rate_at_month,
        r_1.base_rate                             as rate_lag_1m,
        r_2.base_rate                             as rate_lag_2m,
        r_3.base_rate                             as rate_lag_3m,
        r_6.base_rate                             as rate_lag_6m,
        r_0.base_rate - r_1.base_rate             as rate_change_1m,
        r_0.base_rate - r_2.base_rate             as rate_change_2m,
        r_0.base_rate - r_3.base_rate             as rate_change_3m,
        r_0.base_rate - r_6.base_rate             as rate_change_6m
    from monthly_txns t
    left join rate_at_month r_0
        on t.month = r_0.calendar_month
    left join rate_at_month r_1
        on date_trunc(date_sub(t.month, interval 1 month), month) = r_1.calendar_month
    left join rate_at_month r_2
        on date_trunc(date_sub(t.month, interval 2 month), month) = r_2.calendar_month
    left join rate_at_month r_3
        on date_trunc(date_sub(t.month, interval 3 month), month) = r_3.calendar_month
    left join rate_at_month r_6
        on date_trunc(date_sub(t.month, interval 6 month), month) = r_6.calendar_month
)

select * from lagged
