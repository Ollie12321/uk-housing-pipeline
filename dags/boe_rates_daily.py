"""Daily BoE base rate pipeline: extract → GCS → BigQuery → Pub/Sub (if changed) → dbt."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_ROOT = os.environ.get("PIPELINE_ROOT", "/opt/airflow/project")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DBT_ARGS = [
    "--project-dir", f"{PROJECT_ROOT}/dbt",
    "--profiles-dir", f"{PROJECT_ROOT}/dbt",
]


def _extract(**context):
    from extract.boe_rates import extract_boe_rates
    result = extract_boe_rates()
    context["ti"].xcom_push(key="gcs_uri", value=result["gcs_uri"])
    context["ti"].xcom_push(key="rate_changed", value=result["rate_changed"])
    context["ti"].xcom_push(key="current_rate", value=result["current"]["base_rate"])
    return result


def _load(**context):
    from load.bq_loader import load_boe_rates
    gcs_uri = context["ti"].xcom_pull(task_ids="extract_boe_rates", key="gcs_uri")
    return load_boe_rates(gcs_uri)


def _run_dbt(**context):
    env = os.environ.copy()
    subprocess.run(
        ["dbt", "run", "--select", "stg_boe_rates int_rates_reconciled rate_change_events", *DBT_ARGS],
        check=True, env=env,
    )
    subprocess.run(
        ["dbt", "test", "--select", "stg_boe_rates int_rates_reconciled", *DBT_ARGS],
        check=True, env=env,
    )


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="boe_rates_daily",
    default_args=default_args,
    description="Daily BoE base rate extract, load, optional Pub/Sub publish, and dbt models",
    schedule="0 8 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["boe_rates", "batch", "streaming"],
) as dag:
    extract_task = PythonOperator(
        task_id="extract_boe_rates",
        python_callable=_extract,
    )

    load_task = PythonOperator(
        task_id="load_to_bq_raw",
        python_callable=_load,
    )

    dbt_task = PythonOperator(
        task_id="run_dbt_models",
        python_callable=_run_dbt,
    )

    extract_task >> load_task >> dbt_task
