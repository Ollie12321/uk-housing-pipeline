# LinkedIn Showcase Guide

## What to Post (and When)

Post **three times** at 3-day intervals. Each post gets more specific.
Posting a series outperforms a single post algorithmically and shows depth.

---

## Post 1 — The Architecture (Day 1)

**Goal:** Reach, impressions. Architecture diagrams perform very well.

**What to attach:**
- Screenshot of the architecture diagram from the README
- Screenshot of the dbt docs DAG view (the lineage graph)

**Caption template:**

---

I built an end-to-end data pipeline to answer one question:

**How do Bank of England rate changes actually move the UK housing market — and how long is the lag?**

The stack:
→ HM Land Registry (30 years of transactions)
→ Bank of England API (daily rate pulls)
→ UK gilt yields via yfinance
→ GCP: GCS + BigQuery + Pub/Sub
→ dbt (staging → intermediate → marts)
→ Great Expectations for data quality gates
→ Terraform for infra-as-code
→ GitHub Actions CI/CD

The interesting engineering problem: interest rates don't change every day, but you still need real-time capture when they do. I built a hybrid batch + streaming layer — the daily batch loads history, and a Pub/Sub subscriber streams rate changes into BigQuery within seconds of detection.

Architecture diagram and full repo in the comments 👇

#DataEngineering #GCP #BigQuery #dbt #Python #Airflow

---

**First comment:** GitHub repo link + dbt docs site link

---

## Post 2 — The Insight (Day 4)

**Goal:** Engagement. Lead with the data, not the tech.

**What to attach:**
- Screenshot of Chart 1 (volume vs rate time series) from Looker Studio
- Screenshot of Chart 4 (regional sensitivity bar chart)

**Caption template:**

---

After loading 30 years of Land Registry data into BigQuery, one pattern stood out immediately.

**[Insert your headline number here — e.g.: "London detached home transactions fell 23% on average in the 3 months following a rate hike"]**

The variation by region surprised me:
• London: sharp, fast drop within 6 weeks
• Yorkshire: slower, but larger long-term decline
• South East: most sensitive overall

This makes sense — higher LTV mortgages in expensive regions = more rate sensitivity.

The dbt model that surfaces this joins 30 years of monthly transactions to the prevailing rate at 0, 1, 2, 3, and 6 month lags. The lag analysis is the centrepiece of the project.

Live dashboard: [link]

#DataEngineering #Housing #BankOfEngland #Looker

---

## Post 3 — The Engineering Detail (Day 7)

**Goal:** Credibility with technical hiring managers and senior engineers.

**What to attach:**
- Screenshot of the incremental model SQL
- Screenshot of the Great Expectations validation result
- Screenshot of GitHub Actions green CI run

**Caption template:**

---

The most technically interesting part of this pipeline isn't the SQL — it's keeping it cheap and correct on 30 years of Land Registry data.

Three decisions that set it apart from junior projects:

**1. Incremental dbt models**
Full refreshes on 900k+ rows per year × 30 years = slow and wasteful. The `monthly_transactions_by_region` model uses `is_incremental()` with a 1-month overlap to catch late-arriving transactions. A full refresh takes 4 minutes. Incremental runs: 8 seconds.

**2. Data quality gates**
Great Expectations runs between GCS upload and BigQuery load. If Land Registry data arrives with null prices or invalid property types, the pipeline aborts before anything reaches the warehouse. No silent bad data.

**3. Hybrid batch + streaming**
The BoE changes rates maybe 8 times a year. But when it does, you want it in dashboards in seconds, not the next morning. A Pub/Sub subscriber streams rate change events to BigQuery immediately. A reconciliation model in dbt unions batch and streaming, deduplicated by effective date.

GitHub + dbt docs in the comments.

#DataEngineering #dbt #BigQuery #Python #SoftwareEngineering

---

## Screenshot Checklist

Before posting, get screenshots of all of these:

### Architecture
- [ ] Full architecture diagram (from README or draw it in draw.io / Excalidraw)
- [ ] dbt docs lineage DAG (run `dbt docs serve` → open in browser)

### Looker Studio
- [ ] Chart 1: Transaction volume vs base rate (full 15-year view)
- [ ] Chart 2: Rate change events timeline (2021–present shows the hike cycle clearly)
- [ ] Chart 4: Regional sensitivity bar chart (all regions, detached)
- [ ] Full dashboard overview (wide screenshot showing all 5 panels)

### Code
- [ ] `rate_lag_analysis.sql` open in your IDE (VS Code / Cursor)
- [ ] GitHub Actions passing (green ticks)
- [ ] GitHub repo root with clean README rendering

### Data
- [ ] BigQuery table list showing all 4 raw + staging + marts tables
- [ ] A query result showing your headline insight number

---

## Quick-Draw Architecture Diagram

For a polished diagram (better than ASCII), paste this into [Excalidraw](https://excalidraw.com):

**Boxes to draw:**
```
[Land Registry CSV] ──► [GCS bucket] ──► [BigQuery: raw] ──► [dbt staging]
[BoE API] ──────────────────────────────────────────────► [dbt staging]
[BoE API] ──rate change──► [Pub/Sub] ──► [BQ streaming] ──► [dbt staging]
[yfinance] ─────────────────────────────────────────────► [dbt staging]
                                                             │
[Great Expectations gate] ──────────────────────────────────┘
                                                             │
                                                    [dbt intermediate]
                                                             │
                                                       [dbt marts]
                                                             │
                                              [Looker Studio dashboard]

[Terraform] ──► provisions all GCP resources
[GitHub Actions] ──► dbt test on PR + docs on merge
[Airflow] ──► orchestrates all DAGs
```

Use Excalidraw's hand-drawn style — it photographs well and looks more considered than a generic diagram tool.
