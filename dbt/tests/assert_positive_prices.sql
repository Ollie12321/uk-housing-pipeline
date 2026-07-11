/*
  Fails if any transaction has a price of zero or less.
  Land Registry records £1 nominal transfers which are legitimate but
  extremely rare — we keep them; anything <= 0 is a data quality error.
*/

select
    transaction_id,
    price
from {{ ref('stg_transactions') }}
where price <= 0
