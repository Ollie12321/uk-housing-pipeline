# Looker Studio Dashboard Setup

This guide builds the five-panel dashboard you can showcase on LinkedIn.
Total time: ~45 minutes.

---

## 1. Connect to BigQuery

1. Go to [lookerstudio.google.com](https://lookerstudio.google.com) → **Create** → **Report**
2. Select **BigQuery** as the data source
3. Authenticate with the same Google account that owns your GCP project
4. Add these three data sources (you'll switch between them per chart):

| Data source name | Project | Dataset | Table |
|-----------------|---------|---------|-------|
| `rate_lag_analysis` | your-project-id | marts | rate_lag_analysis |
| `regional_sensitivity` | your-project-id | marts | regional_sensitivity |
| `rate_change_events` | your-project-id | marts | rate_change_events |
| `monthly_transactions_by_region` | your-project-id | marts | monthly_transactions_by_region |

---

## 2. Dashboard Layout

Create a **1920×1080** canvas (Theme and Layout → Canvas Size → Custom).
Use this grid:

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER: "How Bank of England Rate Changes Move the Housing     │
│           Market — 30 Years of Evidence"                        │
├──────────────────────────┬──────────────────────────────────────┤
│  Chart 1                 │  Chart 2                             │
│  Transaction volume      │  Rate change timeline                │
│  vs base rate (line)     │  (annotated line)                    │
├──────────────────────────┼──────────────────────────────────────┤
│  Chart 3                 │  Chart 4                             │
│  Lag heatmap             │  Regional sensitivity bar chart      │
│  (pivot table)           │                                      │
├──────────────────────────┴──────────────────────────────────────┤
│  Chart 5: Price band comparison (detached vs flat, by region)   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Chart-by-Chart Configuration

### Chart 1 — Transaction Volume vs Base Rate (Time Series)

**Data source:** `rate_lag_analysis`

| Setting | Value |
|---------|-------|
| Chart type | Combo chart (line + line) |
| Dimension | `month` |
| Metric 1 | `SUM(transaction_count)` → label: "Transactions" |
| Metric 2 | `AVG(rate_at_month)` → label: "Base Rate (%)" |
| Breakdown dimension | none (national view) |
| Date range | Last 15 years |
| Filter | `region` = All (or add a filter control) |

**Right axis:** assign Base Rate to secondary axis.

Add a **Region** filter dropdown (Filter Control → Dimension: `region`).

---

### Chart 2 — Rate Change Events Timeline (Annotated Line)

**Data source:** `rate_change_events`

| Setting | Value |
|---------|-------|
| Chart type | Line chart with reference lines |
| Dimension | `effective_date` |
| Metric | `rate_change_bps` (bar) |
| Breakdown | `direction` (use green for cut, red for hike) |
| Sort | `effective_date` ascending |

Set colour for `direction`:
- `hike` → Red (#D32F2F)
- `cut` → Green (#388E3C)

Add a **Scorecard** widget below showing:
- Current base rate: `MAX(base_rate)` from `int_rates_reconciled`
- Total hikes since 2021: `COUNT(direction='hike')` filtered

---

### Chart 3 — Lag Heatmap (How Long Until Markets React?)

**Data source:** `rate_lag_analysis`

This is the most impressive chart for interviews.

| Setting | Value |
|---------|-------|
| Chart type | Pivot table with heatmap |
| Row dimension | `region` |
| Column dimension | Custom calculated field (see below) |
| Metric | `AVG(transaction_count)` |

Create a **calculated field** called `Rate Change Bucket`:
```
CASE
  WHEN rate_change_1m > 0.25 THEN "Hike >25bp"
  WHEN rate_change_1m < -0.25 THEN "Cut >25bp"
  ELSE "Stable"
END
```

Enable **heatmap colouring** on the metric (green = high volume, red = low).

This shows at a glance which regions are most sensitive to rate moves.

---

### Chart 4 — Regional Sensitivity Ranking (Bar Chart)

**Data source:** `regional_sensitivity`

| Setting | Value |
|---------|-------|
| Chart type | Horizontal bar chart |
| Dimension | `region` |
| Metric | `sensitivity_score` |
| Sort | `sensitivity_score` descending |
| Filter | `property_type` = D (Detached) — or add a property type control |
| Bars | Top 15 regions only (`RANK` filter) |

Colour rule: gradient from light to dark blue by `sensitivity_score`.

Add a **Property Type** filter control.

---

### Chart 5 — Price Band Comparison (Scatter)

**Data source:** `rate_lag_analysis`

| Setting | Value |
|---------|-------|
| Chart type | Scatter chart |
| X axis | `rate_change_3m` (3-month rate change) |
| Y axis | `AVG(avg_price)` |
| Bubble size | `SUM(transaction_count)` |
| Breakdown dimension | `property_type` |
| Filter | Top 5 regions by transaction volume |

Colour by `property_type`:
- D (Detached) → Dark blue
- F (Flat) → Orange
- S (Semi) → Teal
- T (Terraced) → Purple

This chart is the "money shot" — it visually shows that detached homes
are far more sensitive to rate rises than flats.

---

## 4. Finishing Touches

### Header
- Font: Google Sans, 28px, dark navy background
- Subtitle: "Source: HM Land Registry · Bank of England · Personal project"

### Theme
Go to **Theme and Layout** → pick **Metropolis** or set custom:
- Background: #F8F9FA
- Accent: #1A237E (dark navy)
- Font: Google Sans

### Filters
Add these global filter controls at the top of the dashboard:
1. **Date range** control (connects to `month` across all charts)
2. **Region** dropdown (connects to `region`)
3. **Property Type** dropdown (connects to `property_type`)

### Share settings
**File → Share → Manage access → Anyone with the link can view**

Copy the link — this is what goes on LinkedIn.

---

## 5. Key Insight to Highlight

Before you post, run this BigQuery query to find your headline number:

```sql
SELECT
    region,
    AVG(CASE WHEN rate_change_1m > 0 THEN
        (transaction_count - LAG(transaction_count, 3) OVER (PARTITION BY region ORDER BY month))
        / NULLIF(LAG(transaction_count, 3) OVER (PARTITION BY region ORDER BY month), 0) * 100
    END) AS avg_pct_drop_after_hike
FROM `your-project.marts.rate_lag_analysis`
WHERE month >= '2008-01-01'
GROUP BY region
ORDER BY avg_pct_drop_after_hike
LIMIT 5;
```

The region with the biggest negative number is your headline:
*"X transaction volumes fell by Y% on average in the 3 months following a rate hike"*

That's the concrete insight that makes your LinkedIn post land.
