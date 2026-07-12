# Looker Studio Dashboard Setup

This guide builds a six-panel dashboard you can showcase on LinkedIn.
Total time: ~60 minutes.

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

## 2. Page Layout & Dimensions

Set the page canvas to **1200 × 1100 px**: Theme and Layout → Layout → set Width=1200, Height=1100.

The dashboard is divided into four horizontal bands:

```
┌─────────────────────────────────────────────────────────┐  y=15,  h=50
│  HEADER  Title + subtitle (full width text box)         │
├────────────────┬────────────────┬───────────────────────┤  y=75,  h=70
│  Scorecard 1   │  Scorecard 2   │  Scorecard 3          │
│  Current Rate  │  Total Trans.  │  Avg Detached Price   │
├───────────────────────────────────┬─────────────────────┤  y=155, h=330
│  Chart 1 — Volume vs Rate         │  Chart 2 — Rate      │
│  Combo chart (bars + line)        │  Change Events       │
│  w=740                            │  w=440               │
├──────────────────────┬────────────┴──────────────────────┤  y=495, h=300
│  Chart 3 — Heatmap   │  Chart 6 — Avg Price Over Time    │
│  Pivot table         │  Line chart                       │
│  w=580               │  w=600                            │
├──────────────────────┬───────────────────────────────────┤  y=805, h=280
│  Chart 4 — Regional  │  Chart 5 — Price vs Rate Scatter  │
│  Sensitivity Bars    │  Scatter chart                    │
│  w=580               │  w=600                            │
└──────────────────────┴───────────────────────────────────┘
```

**Exact positions** (x, y, width, height — all in px, 20px left margin):

| Element | x | y | w | h |
|---------|---|---|---|---|
| Header text box | 20 | 15 | 1160 | 50 |
| Scorecard 1 (Current Rate) | 20 | 75 | 370 | 65 |
| Scorecard 2 (Total Transactions) | 410 | 75 | 370 | 65 |
| Scorecard 3 (Avg Detached Price) | 800 | 75 | 380 | 65 |
| Chart 1 — Volume vs Rate | 20 | 155 | 740 | 330 |
| Chart 2 — Rate Change Events | 780 | 155 | 400 | 330 |
| Chart 3 — Heatmap | 20 | 495 | 575 | 300 |
| Chart 6 — Avg Price Over Time | 615 | 495 | 565 | 300 |
| Chart 4 — Regional Sensitivity | 20 | 805 | 575 | 280 |
| Chart 5 — Price vs Rate Scatter | 615 | 805 | 565 | 280 |

To set position/size: click a chart → Position and size panel (bottom right) → enter values exactly.

---

## 3. Date Range

All charts using `rate_lag_analysis` share the same date range: **Custom: 1997-01-01 → today**

- Transaction data: Jan 1997 → May 2026 (178k rows in `rate_lag_analysis`)
- BoE rate history starts June 1997 — the rate line on Chart 1 naturally starts there; the 5-month gap in bars before it is expected
- Do **not** use "Last N years" presets — they clip the earliest data

Add a **Date Range Control** (Insert → Date Range Control) connected to the `month` field.
Connect it to Charts 1, 3, 5 and 6 via Edit interactions. Do **not** connect it to Charts 2 or 4.

---

## 4. Key Fields Reference

**`rate_lag_analysis`** (Charts 1, 3, 5, 6)
| Field | Type | Notes |
|-------|------|-------|
| `month` | DATE | First day of each calendar month |
| `broad_region` | STRING | **Use this for filters/grouping** — 10 standard regions |
| `region` | STRING | County-level (130+ values) — too granular for most charts |
| `property_type` | STRING | D=Detached, S=Semi, T=Terraced, F=Flat, O=Other |
| `transaction_count` | INT | Monthly sale count |
| `avg_price` | FLOAT | Average sale price (£) |
| `rate_at_month` | FLOAT | BoE base rate prevailing that month (%) |
| `rate_change_1m` | FLOAT | Rate change vs 1 month prior |
| `rate_change_3m` | FLOAT | Rate change vs 3 months prior |
| `rate_change_6m` | FLOAT | Rate change vs 6 months prior |

**`rate_change_events`** (Chart 2)
| Field | Type | Notes |
|-------|------|-------|
| `effective_date` | DATE | Date rate change took effect |
| `base_rate` | FLOAT | New rate (%) |
| `previous_rate` | FLOAT | Previous rate (%) |
| `rate_change_bps` | FLOAT | Change in basis points |
| `direction` | STRING | `hike` or `cut` |

> This table also has `effective_month` and `source_type` — ignore these for the chart.

**`regional_sensitivity`** (Chart 4)
| Field | Type | Notes |
|-------|------|-------|
| `region` | STRING | County-level (no `broad_region` in this table) |
| `property_type` | STRING | D/S/T/F/O |
| `months_observed` | INT | Number of months of data for this region/type |
| `avg_vol_change_after_hike` | FLOAT | Avg % volume change in 3 months after a rate hike |
| `avg_vol_change_after_cut` | FLOAT | Avg % volume change in 3 months after a rate cut |
| `sensitivity_score` | FLOAT | Composite score — higher = more sensitive to rate changes |

> **If `broad_region` is missing from any field picker:** Resource → Manage added data sources
> → Edit [rate_lag_analysis] → **Refresh fields** → Apply. The column was added after first connection.

---

## 5. Scorecards

Add three scorecards (Insert → Scorecard) using the positions in section 2.

| Scorecard | Data source | Metric | Label |
|-----------|-------------|--------|-------|
| Current Base Rate | `rate_change_events` | `MAX(base_rate)` | "Current Base Rate (%)" |
| Total Transactions | `rate_lag_analysis` | `SUM(transaction_count)` | "Transactions (1997–2026)" |
| Avg Detached Price | `rate_lag_analysis` | `AVG(avg_price)` with filter `property_type = D` | "Avg Detached Price (£)" |

Style: compact font, no border, background `#1A237E`, text white.

---

## 6. Chart-by-Chart Configuration

### Chart 1 — Transaction Volume vs Base Rate

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

After adding both metrics, click `AVG(rate_at_month)` → toggle **"Right axis"** on.

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
| **Record limit** | **100** (default is 10 — this is why only 1997–1999 shows initially) |
| Date range | **Auto: All data** |

> **If chart only shows 1997–1999:** Data tab → "Number of bars" (or "Row limit") → set to **100**.

> **Do not** connect the global Date Range control to this chart — it uses `effective_date` not `month`.

Colours for `direction` breakdown:
- `hike` → Red (`#D32F2F`)
- `cut` → Green (`#388E3C`)

---

### Chart 3 — Lag Heatmap (How Long Until Markets React?)

**Data source:** `rate_lag_analysis`

| Setting | Value |
|---------|-------|
| Chart type | **Pivot table** |
| Row dimension | `broad_region` (**not** `region` — causes "invalid dimension") |
| Column dimension | Calculated field `Rate Change Bucket` (see below) |
| Metric | `AVG(transaction_count)` |
| Date range | **Custom: 1997-06-01 to today** |

Calculated field `Rate Change Bucket`:
```
CASE
  WHEN rate_change_1m > 0.25 THEN "Hike >25bp"
  WHEN rate_change_1m < -0.25 THEN "Cut >25bp"
  ELSE "Stable"
END
```
*(Data panel → Add a field → paste formula)*

Enable **heatmap colouring**: click the metric → turn on Heatmap → green (high) → red (low).

---

### Chart 4 — Regional Sensitivity Ranking

**Data source:** `regional_sensitivity`

| Setting | Value |
|---------|-------|
| Chart type | **Horizontal bar chart** |
| Dimension | `region` (county-level — top 15 keeps it readable) |
| Metric | `sensitivity_score` |
| Sort | `sensitivity_score` descending |
| Record limit | 15 |
| Date range | n/a (no date field in this table) |

Colour gradient: Style → Bar colour → dark navy (`#1A237E`) for max, light blue (`#BBDEFB`) for min.

Add a **Property Type** filter control: Insert → Filter Control → `property_type`.

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
| Filter | `broad_region` IN (London, South East, South West, West Midlands, North West) |

Colours: D=Dark blue, S=Teal, T=Purple, F=Orange.

---

### Chart 6 — Average Sale Price Over Time *(new)*

**Data source:** `rate_lag_analysis`

| Setting | Value |
|---------|-------|
| Chart type | **Line chart** |
| Dimension | `month` |
| Breakdown dimension | `property_type` |
| Metric | `AVG(avg_price)` → label "Avg Sale Price (£)" |
| Date range | **Custom: 1997-01-01 to today** |
| Sort | `month` ascending |

> This chart tells the price story alongside Chart 1's volume story. The divergence between
> Detached (steep rise) and Flat (shallow rise) is the standout visual — especially during the
> 2022–2023 hike cycle where flat prices stagnated while detached remained elevated.

Colours: match Chart 5 — D=Dark blue, S=Teal, T=Purple, F=Orange, O=Grey.

---

## 7. Global Filter Controls

Add these controls using the positions below, placed in the header band (y=75 area):

| Control | Data source | Field | Position |
|---------|-------------|-------|----------|
| Date Range | `rate_lag_analysis` | `month` | Top left |
| Broad Region dropdown | `rate_lag_analysis` | `broad_region` | Top centre |
| Property Type dropdown | `rate_lag_analysis` | `property_type` | Top right |

Connect each control: click it → Edit interactions → tick Charts 1, 3, 5, 6.
Do **not** tick Charts 2 or 4 — they use different data sources/date fields.

---

## 8. Finishing Touches

### Header text box
- Title: **"How BoE Rate Changes Move the UK Housing Market"**
- Subtitle: "HM Land Registry · Bank of England · 1997–2026 · Personal project"
- Background: `#1A237E`, text white, font Google Sans 22px

### Theme
Theme and Layout → custom:
- Background: `#F8F9FA`
- Accent: `#1A237E`
- Font: Google Sans

### Share
**File → Share → Manage access → Anyone with the link can view**

---

## 9. Key Insight SQL

Run in BigQuery to find your LinkedIn headline number:

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

The region with the biggest negative number is your headline:
*"[Region] detached home transactions fell by X% on average in the 3 months following a BoE rate hike — across 29 years of data"*
