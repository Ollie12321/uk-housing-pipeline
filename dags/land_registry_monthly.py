"""Land Registry monthly pipeline: extract → GCS → BigQuery → dbt."""

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


def _extract(**context):
    from extract.land_registry import extract_land_registry

    gcs_uri = extract_land_registry()
    context["ti"].xcom_push(key="gcs_uri", value=gcs_uri)
    return gcs_uri


def _load(**context):
    from load.bq_loader import load_land_registry

    gcs_uri = context["ti"].xcom_pull(task_ids="extract_land_registry", key="gcs_uri")
    return load_land_registry(gcs_uri)


def _run_dbt(**context):
    env = os.environ.copy()
    dbt_dir = f"{PROJECT_ROOT}/dbt"
    dbt_args = ["--project-dir", dbt_dir, "--profiles-dir", dbt_dir]
    subprocess.run(["dbt", "run", "--select", "staging", *dbt_args], check=True, env=env)
    subprocess.run(["dbt", "test", "--select", "staging", *dbt_args], check=True, env=env)


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="land_registry_monthly",
    default_args=default_args,
    description="Monthly Land Registry extract, load, and dbt staging",
    schedule="0 9 1 * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["land_registry", "batch"],
) as dag:
    extract_task = PythonOperator(
        task_id="extract_land_registry",
        python_callable=_extract,
    )

    load_task = PythonOperator(
        task_id="load_to_bq_raw",
        python_callable=_load,
    )

    dbt_task = PythonOperator(
        task_id="run_dbt_staging",
        python_callable=_run_dbt,
    )

    extract_task >> load_task >> dbt_task
