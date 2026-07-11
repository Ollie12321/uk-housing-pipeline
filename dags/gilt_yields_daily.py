"""Daily gilt yields pipeline: yfinance → GCS → BigQuery → dbt."""

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
    from extract.gilt_yields import extract_gilt_yields
    gcs_uri = extract_gilt_yields()
    context["ti"].xcom_push(key="gcs_uri", value=gcs_uri)
    return gcs_uri


def _load(**context):
    from load.bq_loader import load_gilt_yields
    gcs_uri = context["ti"].xcom_pull(task_ids="extract_gilt_yields", key="gcs_uri")
    return load_gilt_yields(gcs_uri)


def _run_dbt(**context):
    env = os.environ.copy()
    subprocess.run(
        ["dbt", "run", "--select", "stg_gilt_yields int_transactions_with_rates", *DBT_ARGS],
        check=True, env=env,
    )
    subprocess.run(
        ["dbt", "test", "--select", "stg_gilt_yields", *DBT_ARGS],
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
    dag_id="gilt_yields_daily",
    default_args=default_args,
    description="Daily UK gilt yield extract from yfinance, load to BigQuery, and dbt staging",
    schedule="0 8 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["gilts", "batch"],
) as dag:
    extract_task = PythonOperator(
        task_id="extract_gilt_yields",
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
