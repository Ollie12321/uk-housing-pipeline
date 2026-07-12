{{
    config(
        materialized='table',
        description='Ranks regions by how strongly transaction volumes respond to rate changes.'
    )
}}

/*
  For each region, computes the average percentage change in transaction
  volume in the 1-, 2-, and 3-month windows following a rate change event.

  A high negative sensitivity_score means transaction volumes fall sharply
  after a rate hike (more sensitive / rate-dependent buyer base).
  A low magnitude means the market is relatively insensitive to rate moves.
*/

with lag_data as (
    select * from {{ ref('rate_lag_analysis') }}
    where property_type in ('D', 'S', 'T', 'F')  -- exclude 'Other' property type
      and broad_region != 'Other England'          -- exclude catch-all bucket (unmapped counties)
),

-- Aggregate to broad_region level first to avoid small-county skew
-- (county-level percentages are unstable where volumes are very low)
broad as (
    select
        month,
        broad_region,
        property_type,
        sum(transaction_count) as transaction_count,
        rate_change_1m,
        rate_change_3m
    from lag_data
    group by 1, 2, 3, 5, 6
),

-- Rolling 3-month average to smooth volatility
smoothed as (
    select
        month,
        broad_region,
        property_type,
        transaction_count,
        avg(transaction_count) over (
            partition by broad_region, property_type
            order by month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_txns,
        rate_change_1m,
        rate_change_3m
    from broad
),

with_pct_change as (
    select
        month,
        broad_region,
        property_type,
        transaction_count,
        rolling_3m_avg_txns,
        rate_change_1m,
        rate_change_3m,
        safe_divide(
            rolling_3m_avg_txns - lag(rolling_3m_avg_txns, 3) over (
                partition by broad_region, property_type order by month
            ),
            lag(rolling_3m_avg_txns, 3) over (
                partition by broad_region, property_type order by month
            )
        ) * 100 as pct_vol_change_3m
    from smoothed
    where rate_change_1m is not null
),

sensitivity as (
    select
        broad_region,
        property_type,
        count(*) as months_observed,
        avg(pct_vol_change_3m) as avg_pct_vol_change_3m,
        corr(rate_change_3m, pct_vol_change_3m) as rate_volume_correlation,
        avg(case when rate_change_1m > 0 then pct_vol_change_3m end)
            as avg_vol_change_after_hike,
        avg(case when rate_change_1m < 0 then pct_vol_change_3m end)
            as avg_vol_change_after_cut
    from with_pct_change
    where pct_vol_change_3m is not null
    group by 1, 2
    having count(*) >= 12
)

select
    broad_region,
    property_type,
    months_observed,
    round(avg_pct_vol_change_3m, 2)    as avg_pct_vol_change_3m,
    round(rate_volume_correlation, 4)  as rate_volume_correlation,
    round(avg_vol_change_after_hike, 2) as avg_vol_change_after_hike,
    round(avg_vol_change_after_cut, 2)  as avg_vol_change_after_cut,
    round(
        abs(avg_vol_change_after_hike - avg_vol_change_after_cut) / 2,
        2
    ) as sensitivity_score
from sensitivity
order by sensitivity_score desc
