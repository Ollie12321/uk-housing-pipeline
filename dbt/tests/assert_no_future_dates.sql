/*
  Fails if any transaction is dated in the future.
  Late-arriving data is expected; future-dated records are always an error.
*/

select
    transaction_id,
    transaction_date
from {{ ref('stg_transactions') }}
where transaction_date > current_date()
