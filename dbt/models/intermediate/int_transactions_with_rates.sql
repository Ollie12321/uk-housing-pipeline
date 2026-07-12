{{
    config(
        materialized='view',
        description='Transactions enriched with the prevailing BoE base rate and gilt yield at time of sale.'
    )
}}

with transactions as (
    select * from {{ ref('stg_transactions') }}
),

rates as (
    select
        effective_month,
        base_rate
    from {{ ref('int_rates_reconciled') }}
),

/*
  We want the rate that was in effect at the time of each transaction.
  Because BoE rates don't change every month, we use an AS-OF join:
  for each transaction_month, find the latest rate whose effective_month
  is <= transaction_month.

  BigQuery doesn't have native AS-OF joins, so we use a correlated
  subquery / window pattern instead.
*/

monthly_rates as (
    -- Expand the rate series to every calendar month between min and max
    -- by carrying each rate forward until the next change.
    select
        effective_month,
        base_rate,
        lead(effective_month) over (order by effective_month) as next_change_month
    from rates
),

transaction_months as (
    select distinct
        date_trunc(transaction_date, month) as transaction_month
    from transactions
),

rate_for_month as (
    select
        tm.transaction_month,
        r.base_rate
    from transaction_months tm
    left join monthly_rates r
        on tm.transaction_month >= r.effective_month
        and (r.next_change_month is null or tm.transaction_month < r.next_change_month)
),

gilts as (
    select
        date_trunc(date, month) as yield_month,
        avg(yield_pct) as avg_yield_pct
    from {{ ref('stg_gilt_yields') }}
    group by 1
),

final as (
    select
        t.transaction_id,
        t.price,
        t.transaction_date,
        date_trunc(t.transaction_date, month) as transaction_month,
        t.postcode,
        t.property_type,
        t.old_new,
        t.duration,
        t.town_city,
        t.region,
        t.broad_region,
        rfm.base_rate,
        g.avg_yield_pct as gilt_yield_pct
    from transactions t
    left join rate_for_month rfm
        on date_trunc(t.transaction_date, month) = rfm.transaction_month
    left join gilts g
        on date_trunc(t.transaction_date, month) = g.yield_month
)

select * from final
