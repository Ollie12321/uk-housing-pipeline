# UK Housing Market Analytics Platform

An end-to-end production-style GCP data engineering pipeline built around one question:

> **How do Bank of England base rate changes impact UK property transaction volumes and prices — and how long is the lag?**

---

## Stack

| Layer | Technology |
|-------|-----------|
| Infrastructure | Terraform |
| Orchestration | Apache Airflow (Docker) |
| Storage | Google Cloud Storage |
| Warehouse | BigQuery (partitioned + clustered) |
| Transform | dbt (staging → intermediate → marts) |
| Streaming | GCP Pub/Sub → BigQuery streaming insert |
| Data quality | Great Expectations |
| CI/CD | GitHub Actions |
| Serving | Looker Studio |

---

## Architecture

```
Land Registry CSV ──┐
                    ├─► GCS (raw) ──► BigQuery raw ──► dbt ──► Looker Studio
BoE API (daily) ────┤             ┌───┘
                    │             │  Great Expectations gate between GCS → BQ
yfinance (gilts) ───┘             │
                                  │
BoE API (rate change?) ─► Pub/Sub ─► BQ streaming insert
                                  │
                                  └─► int_rates_reconciled
                                      (batch + streaming unified)
```

---

## Quick Start

### 1. Prerequisites

- GCP project with billing enabled
- [Terraform](https://terraform.io) ≥ 1.5
- Python 3.11+
- Docker + Docker Compose

### 2. Configure

```bash
cd uk-housing-pipeline
cp .env.example .env
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
cp dbt/profiles.yml.example dbt/profiles.yml
```

Edit `.env` and `terraform/terraform.tfvars` with your GCP project ID and bucket name.
Place your service account JSON key at `secrets/gcp-sa-key.json`.

### 3. Provision GCP infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

This creates: GCS bucket, BigQuery datasets (raw/staging/marts), all tables with partitioning and clustering, Pub/Sub topic + subscription, and a service account with least-privilege IAM bindings.

### 4. Install Python dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)
```

### 5. Run pipelines manually

```bash
# Land Registry (monthly)
python scripts/run_land_registry.py

# BoE base rate (daily — also publishes to Pub/Sub on rate change)
python -m extract.boe_rates

# Gilt yields (daily)
python -m extract.gilt_yields

# Pub/Sub → BQ streaming (run persistently, e.g. in Cloud Run)
python -m streaming.pubsub_to_bq
```

### 6. Run dbt

```bash
cd dbt
dbt deps
dbt run          # all models
dbt test         # all tests including custom assertions
dbt docs generate && dbt docs serve
```

### 7. Local Airflow

```bash
docker compose up airflow-init
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080) (admin / admin). Three DAGs are available:
- `land_registry_monthly` — 1st of each month at 09:00
- `boe_rates_daily` — every day at 08:00
- `gilt_yields_daily` — every day at 08:00

---

## dbt Model DAG

```
stg_transactions ──────────────────────────────────────────────────┐
                                                                    │
stg_boe_rates ────────────────────────────────────────────────┐    │
stg_boe_rate_events_streaming ──► int_rates_reconciled ───────┤    ├──► monthly_transactions_by_region
                                                              │    │        │
stg_gilt_yields ──────────────────────────────────────────────┴────┴──► int_transactions_with_rates
                                                                             │
int_rates_reconciled ──► rate_change_events                                  │
                                                                             │
rate_change_events + monthly_transactions_by_region ──► rate_lag_analysis   │
                                                                             │
rate_lag_analysis ──► regional_sensitivity                                   │
```

---

## Project Layout

```
uk-housing-pipeline/
├── .github/workflows/      CI/CD (dbt test on PR, docs deploy on merge)
├── config/                 Shared settings (env-backed)
├── dags/                   Airflow DAGs
│   ├── land_registry_monthly.py
│   ├── boe_rates_daily.py
│   └── gilt_yields_daily.py
├── dbt/
│   ├── models/
│   │   ├── staging/        stg_transactions, stg_boe_rates, stg_gilt_yields, stg_boe_rate_events_streaming
│   │   ├── intermediate/   int_rates_reconciled, int_transactions_with_rates
│   │   └── marts/          monthly_transactions_by_region (incremental), rate_change_events,
│   │                       rate_lag_analysis, regional_sensitivity
│   ├── macros/             is_incremental_safe, lag_months
│   └── tests/              assert_no_future_dates, assert_positive_prices, assert_lag_analysis_completeness
├── docs/                   data_dictionary.md
├── extract/                land_registry.py, boe_rates.py, gilt_yields.py
├── load/                   bq_loader.py (Land Registry CSV + BoE/gilt NDJSON)
├── quality/                Great Expectations config, suites, checkpoints
├── scripts/                run_land_registry.py (manual run helper)
├── secrets/                .gitignored — place gcp-sa-key.json here
├── streaming/              pubsub_to_bq.py (persistent Pub/Sub subscriber)
├── terraform/              main.tf, variables.tf, iam.tf, outputs.tf
├── .env.example
├── docker-compose.yml
└── requirements.txt
```

---

## GitHub Actions

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `dbt_test.yml` | PR touching `dbt/`, `extract/`, `load/` | `dbt compile` → `dbt run` → `dbt test` — PR cannot merge if tests fail |
| `dbt_docs.yml` | Push to `main` touching `dbt/` | Generates dbt docs and deploys to GitHub Pages |

Required repository secrets: `GCP_SA_KEY`, `GCP_PROJECT_ID`.

---

## Data Sources

| Source | Method | Frequency | Cost |
|--------|--------|-----------|------|
| [Land Registry Price Paid](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads) | Yearly CSV download | Monthly refresh | Free |
| [Bank of England base rate](https://www.bankofengland.co.uk/boeapps/database) | REST API | Daily | Free |
| UK Gilt yields | yfinance (`GB10YT=RR`) | Daily | Free |

---

## Key Design Decisions

- **Incremental model** — `monthly_transactions_by_region` only scans new months on each run, with safe overlap logic (`is_incremental_safe` macro handles late-arriving data)
- **Hybrid batch + streaming** — `int_rates_reconciled` unions both sources; streaming events appear in reports within seconds of a rate change
- **AS-OF join** — `int_transactions_with_rates` uses a carry-forward pattern to assign the prevailing rate to each transaction month without a direct date match
- **BigQuery optimisation** — partitioning + clustering on every hot table, documented in `docs/data_dictionary.md`
- **Data quality gate** — Great Expectations runs between GCS upload and BQ load; the pipeline aborts on failure
- **CI prevents bad code reaching prod** — dbt tests must pass on every PR before merge
