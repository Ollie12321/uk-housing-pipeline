# Looker Studio Dashboard Setup

This guide builds the five-panel dashboard you can showcase on LinkedIn.
Total time: ~45 minutes.

---

## 1. Connect to BigQuery

1. Go to [lookerstudio.google.com](https://lookerstudio.google.com) → **Create** → **Report**
2. Select **BigQuery** as the data source
3. Authenticate with the same Google account that owns `uk-housing-ol-2025`
4. Add these four data sources (you'll switch between them per chart):

| Data source name | Project | Dataset | Table |
|-----------------|---------|---------|-------|
| `rate_lag_analysis` | `uk-housing-ol-2025` | `staging_marts` | `rate_lag_analysis` |
| `rate_change_events` | `uk-housing-ol-2025` | `staging_marts` | `rate_change_events` |
| `regional_sensitivity` | `uk-housing-ol-2025` | `staging_marts` | `regional_sensitivity` |
| `monthly_transactions_by_region` | `uk-housing-ol-2025` | `staging_marts` | `monthly_transactions_by_region` |

> **Dataset name:** The dbt models live in `staging_marts` (not `marts`). Make sure you
> select this exact dataset when connecting — `marts` is an older empty dataset.

---

## 2. Date Range — Apply to All Charts

All charts (except Chart 2) should use the **same date range**: **Custom: 1997-06-01 → today**

- Transaction data covers **Jan 1997 → May 2026** — `rate_lag_analysis` has 178k rows spanning this range
- BoE rate history starts **June 1997** (first MPC decision) — months Jan–May 1997 have transaction counts but NULL `rate_at_month`; use 1997-06-01 as chart start dates to keep rate + transaction data aligned
- Do **not** use "Last N years" presets — Looker Studio counts from today backwards and may clip the earliest data

Add a single **Date Range Control** at the top of the dashboard connected to the `month`
field. This will sync Charts 1, 3 and 5 simultaneously. Chart 2 and Chart 4 use different
date fields — see per-chart notes below.

---

## 3. Key Fields Reference

Before configuring charts, note these field names in the tables:

**`rate_lag_analysis`**
| Field | Type | Notes |
|-------|------|-------|
| `month` | DATE | First day of each calendar month |
| `broad_region` | STRING | **Use this for filters/grouping** — 10 standard regions (London, South East, etc.) |
| `region` | STRING | County-level (130+ values, e.g. SURREY, WEST MIDLANDS) — too granular for most charts |
| `property_type` | STRING | D=Detached, S=Semi, T=Terraced, F=Flat, O=Other |
| `transaction_count` | INT | Monthly sale count |
| `avg_price` | FLOAT | Average sale price (£) |
| `rate_at_month` | FLOAT | BoE base rate prevailing that month (%) |
| `rate_change_1m` | FLOAT | Rate change vs 1 month prior |
| `rate_change_3m` | FLOAT | Rate change vs 3 months prior |
| `rate_change_6m` | FLOAT | Rate change vs 6 months prior |

**`rate_change_events`**
| Field | Type | Notes |
|-------|------|-------|
| `effective_date` | DATE | Date rate change took effect |
| `base_rate` | FLOAT | New rate (%) |
| `previous_rate` | FLOAT | Previous rate (%) |
| `rate_change_bps` | FLOAT | Change in basis points |
| `direction` | STRING | `hike` or `cut` |

**`regional_sensitivity`**
| Field | Type | Notes |
|-------|------|-------|
| `region` | STRING | County-level (no `broad_region` in this table) |
| `property_type` | STRING | D/S/T/F/O |
| `months_observed` | INT | Number of months of data for this region/type |
| `avg_pct_vol_change_3m` | FLOAT | Avg % volume change over 3 months |
| `rate_volume_correlation` | FLOAT | Correlation between rate moves and volume |
| `avg_vol_change_after_hike` | FLOAT | Avg % volume change in 3 months after a rate hike |
| `avg_vol_change_after_cut` | FLOAT | Avg % volume change in 3 months after a rate cut |
| `sensitivity_score` | FLOAT | Composite score — higher = more sensitive to rate changes |

---

## 4. Chart-by-Chart Configuration

### Chart 1 — Transaction Volume vs Base Rate (Combo Chart)

**Data source:** `rate_lag_analysis`

| Setting | Value |
|---------|-------|
| Chart type | **Combo chart** (bars + line) |
| Dimension | `month` |
| Metric 1 | `SUM(transaction_count)` → label "Transactions" → **left Y-axis, bars** |
| Metric 2 | `AVG(rate_at_month)` → label "Base Rate (%)" → **right Y-axis, line** |
| Breakdown | none |
| Date range | **Custom: 1997-01-01 to today** |
| Sort | `month` ascending |

**Setting up dual axis:** After adding both metrics, click `AVG(rate_at_month)` in the
Metric panel → toggle **"Right axis"** on. This keeps the two scales separate (transaction
count vs 0–8% rate).

> Note: the bars start in Jan 1997 but the rate line only appears from Jun 1997 (first MPC decision). The 5-month gap at the start is normal and expected.

Add a **Broad Region** filter dropdown: Insert → Filter Control → Dimension: `broad_region`.

> **If `broad_region` is not visible as a field option:** Resource → Manage added data sources → Edit [rate_lag_analysis] → **Refresh fields** → Apply. This picks up all new columns added since the data source was first connected.

---

### Chart 2 — Rate Change Events Timeline

**Data source:** `rate_change_events`

| Setting | Value |
|---------|-------|
| Chart type | **Bar chart** |
| Dimension | `effective_date` |
| Metric | `rate_change_bps` → label "Change (bps)" |
| Breakdown dimension | `direction` |
| Sort | `effective_date` ascending |
| **Record limit** | **100** (CRITICAL — default is 10, which only shows the first 10 events = 1997–1999) |
| Date range | **Auto: All data** (this table uses `effective_date`, not `month` — the global date range control will NOT connect to it; leave it set to "Auto" on the chart itself) |

> **If chart only shows 1997–1999:** Open the chart → Data tab → find "Row limit" or "Number of bars" → change from 10 to **100**. This is the most common issue with this chart.

> **Do not connect** the global Date Range control to this chart. Since the data source uses `effective_date` (not `month`), the global control will filter it incorrectly.

> The table also has `effective_month` and `source_type` columns — ignore these for the chart.

Set colours for `direction` breakdown:
- `hike` → Red (`#D32F2F`)
- `cut` → Green (`#388E3C`)

Add two **Scorecards** (Insert → Scorecard) to the side using `rate_change_events`:
- `MAX(base_rate)` → label "Current Base Rate"
- `COUNT(direction)` with filter `direction = hike` → label "Total hikes (1997–present)"

---

### Chart 3 — Lag Heatmap (How Long Until Markets React?)

**Data source:** `rate_lag_analysis`

This is the most impressive chart for interviews.

> **If `broad_region` is not in the dimension picker:** The column was added after the data source was first connected. Fix: **Resource → Manage added data sources → Edit [rate_lag_analysis] → click "Refresh fields" → Apply**. The `broad_region` field will then appear.

| Setting | Value |
|---------|-------|
| Chart type | **Pivot table** |
| Row dimension | `broad_region` (**not** `region` — `region` is county-level with 130+ values and causes "invalid dimension") |
| Column dimension | Calculated field `Rate Change Bucket` (see below) |
| Metric | `AVG(transaction_count)` |
| Date range | **Custom: 1997-06-01 to today** |

Create a **calculated field** called `Rate Change Bucket`:
```
CASE
  WHEN rate_change_1m > 0.25 THEN "Hike >25bp"
  WHEN rate_change_1m < -0.25 THEN "Cut >25bp"
  ELSE "Stable"
END
```
*(Add via: Data panel → Add a field → enter formula above)*

Enable **heatmap colouring** on the metric:
- Click the metric in the pivot config → turn on Heatmap
- Colour scale: green (high volume) → red (low volume)

This shows at a glance which broad regions lose the most transactions during a hike.

---

### Chart 4 — Regional Sensitivity Ranking (Bar Chart)

**Data source:** `regional_sensitivity`

| Setting | Value |
|---------|-------|
| Chart type | **Horizontal bar chart** |
| Dimension | `region` (county-level — keep top 15 to stay readable) |
| Metric | `sensitivity_score` |
| Sort | `sensitivity_score` descending |
| Record limit | 15 |
| Date range | n/a (no date field in this table) |

Add a **Property Type** filter control (Insert → Filter Control → Dimension: `property_type`).

Colour rule: Style tab → Bar colour → set a single colour gradient. Pick dark navy (`#1A237E`)
for max, light blue (`#BBDEFB`) for min.

---

### Chart 5 — Price vs Rate Change Scatter

**Data source:** `rate_lag_analysis`

| Setting | Value |
|---------|-------|
| Chart type | **Scatter chart** |
| X axis | `AVG(rate_change_3m)` → label "3-Month Rate Change (%)" |
| Y axis | `AVG(avg_price)` → label "Avg Sale Price (£)" |
| Bubble size | `SUM(transaction_count)` |
| Breakdown dimension | `property_type` |
| Date range | **Custom: 1997-06-01 to today** |
| Filter | Add filter: `broad_region` = London, South East, South West, West Midlands, North West (top 5) |

Colour by `property_type`:
- D (Detached) → Dark blue
- S (Semi) → Teal
- T (Terraced) → Purple
- F (Flat) → Orange

This shows that detached homes cluster at higher prices AND show larger drops after rate rises
(they shift left on the X-axis during hike periods).

---

## 5. Global Filters

Add these three controls at the top of the dashboard:

1. **Date Range** control → `month` field → default: Custom 1997-06-01 to today
2. **Broad Region** dropdown → `broad_region` from `rate_lag_analysis`
3. **Property Type** dropdown → `property_type` from `rate_lag_analysis`

To connect a filter control to a chart: click the filter control → Edit interactions →
tick the charts you want it to affect. Charts using different data sources (e.g.
`rate_change_events`) won't connect automatically — only those sharing the same source.

---

## 6. Finishing Touches

### Header
- Title: **"How BoE Rate Changes Move the UK Housing Market"**
- Subtitle: "Source: HM Land Registry · Bank of England · 1997–2026 · Personal project"
- Font: Google Sans, 24px, dark navy background (`#1A237E`)

### Theme
Theme and Layout → custom:
- Background: `#F8F9FA`
- Accent: `#1A237E`
- Font: Google Sans

### Share settings
**File → Share → Manage access → Anyone with the link can view**

Copy the link — this is what goes on LinkedIn.

---

## 7. Key Insight to Highlight

Run this in BigQuery to find your headline number:

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

The region with the biggest negative number is your LinkedIn headline:
*"[Region] detached home transactions fell by X% on average in the 3 months following a BoE rate hike"*
