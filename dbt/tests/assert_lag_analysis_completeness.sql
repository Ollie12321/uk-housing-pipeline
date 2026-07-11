/*
  Fails if the rate_lag_analysis mart has months with transactions but
  no base rate. This would produce silently wrong lag correlation numbers.

  Acceptable gap: the very first months of data (pre-1997) before the
  BoE became independent and the rate series begins.
*/

select
    month,
    region,
    transaction_count
from {{ ref('rate_lag_analysis') }}
where rate_at_month is null
    and month >= date('1997-06-01')  -- BoE independence day
    and transaction_count > 0
