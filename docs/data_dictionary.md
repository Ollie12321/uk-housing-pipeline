# Data Dictionary

## Raw Layer (`raw` dataset)

### `raw.land_registry_transactions`

Source: HM Land Registry Price Paid Data

| Column | Type | Description |
|--------|------|-------------|
| `transaction_id` | STRING | Unique reference for the property transaction |
| `price` | INTEGER | Sale price in GBP |
| `transaction_date` | DATE | Date of transfer |
| `postcode` | STRING | Full UK postcode |
| `property_type` | STRING | D = Detached, S = Semi-detached, T = Terraced, F = Flat/Maisonette, O = Other |
| `old_new` | STRING | Y = Newly built, N = Established |
| `duration` | STRING | F = Freehold, L = Leasehold |
| `paon` | STRING | Primary addressable object name (house number/name) |
| `saon` | STRING | Secondary addressable object name (flat/unit) |
| `street` | STRING | Street name |
| `locality` | STRING | Locality |
| `town_city` | STRING | Town or city |
| `district` | STRING | District |
| `county` | STRING | County (used as `region` in staging and above) |
| `ppd_category` | STRING | A = Standard, B = Additional (non-standard transactions) |
| `record_status` | STRING | A = Addition, C = Change, D = Delete |

Partitioned by: `transaction_date` (MONTH)
Clustered by: `county`, `property_type`

---

### `raw.boe_base_rates`

Source: Bank of England public data API

| Column | Type | Description |
|--------|------|-------------|
| `effective_date` | DATE | Date the rate became effective |
| `base_rate` | FLOAT64 | Official Bank Rate (%) |
| `source` | STRING | Source URL |
| `loaded_at` | TIMESTAMP | Pipeline load timestamp |

Clustered by: `effective_date`

---

### `raw.gilt_yields`

Source: Yahoo Finance (`GB10YT=RR` ticker via yfinance)

| Column | Type | Description |
|--------|------|-------------|
| `date` | DATE | Trading date |
| `yield_pct` | FLOAT64 | UK 10-year gilt yield (%) |
| `ticker` | STRING | Yahoo Finance ticker symbol used |
| `loaded_at` | TIMESTAMP | Pipeline load timestamp |

Partitioned by: `date` (DAY)

---

### `raw.boe_rate_events_streaming`

Source: GCP Pub/Sub (published by `extract/boe_rates.py` on rate change detection)

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | STRING | UUID for the rate change event |
| `effective_date` | DATE | Date the new rate is effective |
| `previous_rate` | FLOAT64 | Rate before the change |
| `new_rate` | FLOAT64 | New rate after the change |
| `published_at` | TIMESTAMP | Pub/Sub publish timestamp |

---

## Staging Layer (`staging` dataset)

### `stg_transactions`

Cleaned Land Registry transactions. Only active records (`record_status = A`) with normalised postcodes.

Key transformations:
- Filters out `record_status != A` (corrections and deletions)
- Drops transactions before `min_transaction_date` (default 1995-01-01)
- Uppercases and trims postcodes
- Renames `county` to `region`

---

### `stg_boe_rates`

Deduplicated BoE rate history. Where the same `effective_date` appears multiple times (daily loads), the most recent `loaded_at` wins.

---

### `stg_gilt_yields`

Deduplicated gilt yields. Same deduplication logic — latest load wins per `date`.

---

### `stg_boe_rate_events_streaming`

Deduplicated streaming events. Idempotent on `event_id`.

---

## Intermediate Layer (`staging` dataset, view materialisation)

### `int_rates_reconciled`

Unions `stg_boe_rates` (batch) and `stg_boe_rate_events_streaming` (streaming). Deduplicates on `effective_date` with streaming events taking priority. Adds `effective_month` for month-grain joins.

**Key design choice:** streaming rows beat batch rows for the same date, ensuring rate changes are visible immediately rather than waiting for the next batch run.

---

### `int_transactions_with_rates`

Joins `stg_transactions` to the prevailing BoE base rate via an AS-OF pattern (carries the last known rate forward into months where no rate change occurred). Also joins monthly average gilt yield.

---

## Marts Layer (`marts` dataset)

### `monthly_transactions_by_region`

**Incremental model.** Aggregates transactions by `month`, `region`, and `property_type`. Includes:
- `transaction_count`
- `avg_price`, `median_price`, `min_price`, `max_price`
- `avg_base_rate`, `avg_gilt_yield_pct` at time of transaction

`unique_key = month_region_key` — safe to re-run (MERGE semantics).

Partitioned by: `month` (MONTH)
Clustered by: `region`, `property_type`

---

### `rate_change_events`

One row per BoE rate change. Includes `direction` (hike/cut), magnitude in basis points, and source type.

---

### `rate_lag_analysis`

The centrepiece model. Monthly transactions per region joined to base rate at 0, 1, 2, 3, and 6 month lags. Adds derived `rate_change_Nm` columns (rate at month − rate N months ago).

Use this model to answer: *"How many months after a rate hike did London transaction volumes peak/trough?"*

Partitioned by: `month` (MONTH)
Clustered by: `region`

---

### `regional_sensitivity`

Ranks regions by `sensitivity_score` — the mean absolute difference in transaction volume response between rate hike and cut episodes. High score = more rate-sensitive market.

Includes `avg_vol_change_after_hike` and `avg_vol_change_after_cut` for directional analysis.
