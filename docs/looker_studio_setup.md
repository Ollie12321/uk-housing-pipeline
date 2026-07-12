# Dashboard Reference

Six-panel Looker Studio dashboard visualising 29 years of UK housing transaction data
(HM Land Registry, 1997–2026) against Bank of England base rate history.

**Live data:** `uk-housing-ol-2025.staging_marts` (BigQuery)
**Rows:** ~35M raw transactions → 178k mart rows across 11 broad regions, 5 property types, 352 months

---

## Data Sources

| Data source | Project | Dataset | Table | Primary key |
|-------------|---------|---------|-------|-------------|
| `rate_lag_analysis` | `uk-housing-ol-2025` | `staging_marts` | `rate_lag_analysis` | month + region + property_type |
| `rate_change_events` | `uk-housing-ol-2025` | `staging_marts` | `rate_change_events` | effective_date |
| `regional_sensitivity` | `uk-housing-ol-2025` | `staging_marts` | `regional_sensitivity` | region + property_type |
| `monthly_transactions_by_region` | `uk-housing-ol-2025` | `staging_marts` | `monthly_transactions_by_region` | month + region + property_type |

---

## Page Layout

Canvas: **1200 × 1100 px**

```
┌─────────────────────────────────────────────────────────┐
│  Header + 3 scorecards (Current Rate / Transactions /   │
│  Avg Price)                                             │
├───────────────────────────────────┬─────────────────────┤
│  Chart 1 — Volume vs Rate         │  Chart 2 — Rate     │
│  Combo chart (bars + line)        │  Change Events      │
│  w=740                            │  w=400              │
├──────────────────────┬────────────┴─────────────────────┤
│  Chart 3 — Heatmap   │  Chart 6 — Avg Price Over Time   │
│  Pivot table         │  Line chart                      │
│  w=580               │  w=580                           │
├──────────────────────┬───────────────────────────────────┤
│  Chart 4 — Regional  │  Chart 5 — Price vs Sensitivity  │
│  Sensitivity Bars    │  Scatter                         │
│  w=580               │  w=580                           │
└──────────────────────┴───────────────────────────────────┘
```

**Element positions (x, y, w, h in px):**

| Element | x | y | w | h |
|---------|---|---|---|---|
| Header text box | 20 | 15 | 1160 | 50 |
| Scorecard — Current Rate | 20 | 75 | 370 | 65 |
| Scorecard — Total Transactions | 410 | 75 | 370 | 65 |
| Scorecard — Avg Sale Price | 800 | 75 | 380 | 65 |
| Chart 1 | 20 | 155 | 740 | 330 |
| Chart 2 | 780 | 155 | 400 | 330 |
| Chart 3 | 20 | 495 | 575 | 300 |
| Chart 6 | 615 | 495 | 565 | 300 |
| Chart 4 | 20 | 805 | 575 | 280 |
| Chart 5 | 615 | 805 | 565 | 280 |

---

## Field Reference

### `rate_lag_analysis`

| Field | Type | Description |
|-------|------|-------------|
| `month` | DATE | First day of calendar month |
| `broad_region` | STRING | 10 standard regions (London, South East, etc.) derived from county via `county_to_region` macro |
| `region` | STRING | County-level (130+ values) |
| `property_type` | STRING | D=Detached, S=Semi, T=Terraced, F=Flat, O=Other |
| `transaction_count` | INT64 | Monthly sale count |
| `avg_price` | FLOAT64 | Average sale price (£) |
| `rate_at_month` | FLOAT64 | BoE base rate prevailing that month (%) |
| `rate_change_1m` | FLOAT64 | Rate Δ vs 1 month prior |
| `rate_change_3m` | FLOAT64 | Rate Δ vs 3 months prior |
| `rate_change_6m` | FLOAT64 | Rate Δ vs 6 months prior |

### `rate_change_events`

| Field | Type | Description |
|-------|------|-------------|
| `effective_date` | DATE | MPC decision date |
| `base_rate` | FLOAT64 | New rate (%) |
| `previous_rate` | FLOAT64 | Previous rate (%) |
| `rate_change_bps` | FLOAT64 | Δ in basis points |
| `direction` | STRING | `hike` \| `cut` |

> Only rows where `base_rate != previous_rate` are included — hold decisions are excluded.
> There are no 2026 entries because the rate has been held at 3.75% since December 2025.

### `regional_sensitivity`

| Field | Type | Description |
|-------|------|-------------|
| `region` | STRING | County-level |
| `property_type` | STRING | D/S/T/F/O |
| `avg_vol_change_after_hike` | FLOAT64 | Avg % volume change in 3 months following a hike |
| `avg_vol_change_after_cut` | FLOAT64 | Avg % volume change in 3 months following a cut |
| `sensitivity_score` | FLOAT64 | Composite score normalised across all regions |

---

## Chart Specifications

### Chart 1 — Transaction Volume vs Base Rate

| Setting | Value |
|---------|-------|
| Type | Combo chart — bars + line |
| Dimension | `month` |
| Metric 1 (bars, left axis) | `SUM(transaction_count)` |
| Metric 2 (line, right axis) | `AVG(rate_at_month)` |
| Date range | 1997-01-01 → today |
| Data source | `rate_lag_analysis` |

---

### Chart 2 — Rate Change Events Timeline

| Setting | Value |
|---------|-------|
| Type | Bar chart |
| Dimension | `effective_date` |
| Metric | `rate_change_bps` |
| Breakdown | `direction` (hike=`#D32F2F`, cut=`#388E3C`) |
| Record limit | 100 |
| Date range | All data (auto) |
| Data source | `rate_change_events` |

> `rate_change_events` uses `effective_date` not `month` — not connected to the global date range control.

---

### Chart 3 — Lag Heatmap

| Setting | Value |
|---------|-------|
| Type | Pivot table with heatmap colouring |
| Row dimension | `broad_region` |
| Column dimension | Calculated: `Rate Change Bucket` |
| Metric | `AVG(transaction_count)` |
| Date range | 1997-06-01 → today |
| Data source | `rate_lag_analysis` |

`Rate Change Bucket` calculated field:
```
CASE
  WHEN rate_change_1m > 0.25 THEN "Hike >25bp"
  WHEN rate_change_1m < -0.25 THEN "Cut >25bp"
  ELSE "Stable"
END
```

---

### Chart 4 — Regional Sensitivity Ranking

| Setting | Value |
|---------|-------|
| Type | Horizontal bar chart |
| Dimension | `region` |
| Metric | `sensitivity_score` |
| Sort | `sensitivity_score` descending |
| Record limit | 15 |
| Data source | `regional_sensitivity` |

---

### Chart 5 — Price vs Rate Sensitivity Scatter

| Setting | Value |
|---------|-------|
| Type | Scatter chart |
| Dimension | `broad_region` |
| Metric X | `AVG(avg_price)` |
| Metric Y | `AVG(sensitivity_score)` — from `regional_sensitivity` |
| Bubble size | `SUM(transaction_count)` |
| Date range | 1997-06-01 → today |
| Data source | `rate_lag_analysis` |

---

### Chart 6 — Average Sale Price Over Time

| Setting | Value |
|---------|-------|
| Type | Line chart |
| Dimension | `month` |
| Breakdown | `property_type` |
| Metric | `AVG(avg_price)` |
| Date range | 1997-01-01 → today |
| Data source | `rate_lag_analysis` |

---

## Global Filter Controls

| Control | Field | Connects to |
|---------|-------|-------------|
| Date Range | `month` | Charts 1, 3, 5, 6 |
| Broad Region | `broad_region` | Charts 1, 3, 5, 6 |
| Property Type | `property_type` | Charts 1, 3, 6 |

---

## Key Insight Query

```sql
SELECT
    broad_region,
    ROUND(AVG(CASE WHEN rate_change_1m > 0 THEN
        (transaction_count - LAG(transaction_count, 3)
            OVER (PARTITION BY broad_region, property_type ORDER BY month))
        / NULLIF(LAG(transaction_count, 3)
            OVER (PARTITION BY broad_region, property_type ORDER BY month), 0) * 100
    END), 1) AS avg_pct_drop_after_hike
FROM `uk-housing-ol-2025.staging_marts.rate_lag_analysis`
WHERE month >= '1997-01-01'
  AND property_type = 'D'
GROUP BY broad_region
ORDER BY avg_pct_drop_after_hike
LIMIT 5;
```
