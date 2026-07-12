{{
    config(
        materialized='incremental',
        unique_key='month_region_key',
        partition_by={
            'field': 'month',
            'data_type': 'date',
            'granularity': 'month'
        },
        cluster_by=['region', 'property_type'],
        on_schema_change='sync_all_columns'
    )
}}

/*
  Incremental model: on first run processes all history.
  On subsequent runs, only processes transactions from the latest
  already-loaded month onwards (avoiding re-scanning 30+ years of data).

  unique_key = month_region_key means BigQuery will MERGE on that key,
  so a re-run of the same month is idempotent.
*/

with source as (
    select * from {{ ref('int_transactions_with_rates') }}

    {% if is_incremental() %}
        where transaction_month >= {{ is_incremental_safe('month', this) }}
    {% endif %}
),

aggregated as (
    select
        date_trunc(transaction_date, month)   as month,
        region,
        broad_region,
        property_type,
        count(*)                              as transaction_count,
        avg(price)                            as avg_price,
        approx_quantiles(price, 100)[offset(50)] as median_price,
        min(price)                            as min_price,
        max(price)                            as max_price,
        avg(base_rate)                        as avg_base_rate,
        avg(gilt_yield_pct)                   as avg_gilt_yield_pct
    from source
    group by 1, 2, 3, 4
)

select
    *,
    concat(cast(month as string), '_', region, '_', property_type) as month_region_key
from aggregated
