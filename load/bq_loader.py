"""Generic GCS → BigQuery loader for all pipeline sources."""

from __future__ import annotations

import json
import logging
from typing import Sequence

from google.cloud import bigquery

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# ── Schemas ────────────────────────────────────────────────────────────────────

LAND_REGISTRY_SCHEMA: Sequence[bigquery.SchemaField] = [
    bigquery.SchemaField("transaction_id", "STRING"),
    bigquery.SchemaField("price", "INTEGER"),
    bigquery.SchemaField("transaction_date", "STRING"),
    bigquery.SchemaField("postcode", "STRING"),
    bigquery.SchemaField("property_type", "STRING"),
    bigquery.SchemaField("old_new", "STRING"),
    bigquery.SchemaField("duration", "STRING"),
    bigquery.SchemaField("paon", "STRING"),
    bigquery.SchemaField("saon", "STRING"),
    bigquery.SchemaField("street", "STRING"),
    bigquery.SchemaField("locality", "STRING"),
    bigquery.SchemaField("town_city", "STRING"),
    bigquery.SchemaField("district", "STRING"),
    bigquery.SchemaField("county", "STRING"),
    bigquery.SchemaField("ppd_category", "STRING"),
    bigquery.SchemaField("record_status", "STRING"),
]

BOE_RATES_SCHEMA: Sequence[bigquery.SchemaField] = [
    bigquery.SchemaField("effective_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("base_rate", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP"),
]

GILT_YIELDS_SCHEMA: Sequence[bigquery.SchemaField] = [
    bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("yield_pct", "FLOAT64"),
    bigquery.SchemaField("ticker", "STRING"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP"),
]


# ── Generic loader ─────────────────────────────────────────────────────────────

def load_gcs_to_bq(
    gcs_uri: str,
    table_id: str,
    schema: Sequence[bigquery.SchemaField],
    settings: Settings | None = None,
    source_format: bigquery.SourceFormat = bigquery.SourceFormat.CSV,
    write_disposition: str = bigquery.WriteDisposition.WRITE_APPEND,
    skip_leading_rows: int = 0,
) -> bigquery.LoadJob:
    settings = settings or get_settings()
    client = bigquery.Client(project=settings.gcp_project_id)

    is_csv = source_format == bigquery.SourceFormat.CSV
    job_config = bigquery.LoadJobConfig(
        source_format=source_format,
        schema=schema,
        write_disposition=write_disposition,
        autodetect=False,
        **({
            "skip_leading_rows": skip_leading_rows,
            "allow_quoted_newlines": True,
            "field_delimiter": ",",
            "null_marker": "",
        } if is_csv else {}),
    )

    logger.info("Loading %s → %s", gcs_uri, table_id)
    job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    job.result()
    table = client.get_table(table_id)
    logger.info("Table now has %s rows", table.num_rows)
    return job


def load_ndjson_to_bq(
    gcs_uri: str,
    table_id: str,
    schema: Sequence[bigquery.SchemaField],
    settings: Settings | None = None,
) -> bigquery.LoadJob:
    return load_gcs_to_bq(
        gcs_uri=gcs_uri,
        table_id=table_id,
        schema=schema,
        settings=settings,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )


# ── Source-specific loaders ────────────────────────────────────────────────────

def load_land_registry(gcs_uri: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    table_id = f"{settings.gcp_project_id}.{settings.bq_raw_dataset}.land_registry_transactions"
    load_gcs_to_bq(gcs_uri=gcs_uri, table_id=table_id, schema=LAND_REGISTRY_SCHEMA, settings=settings)
    return table_id


def load_boe_rates(gcs_uri: str, settings: Settings | None = None) -> str:
    """Load a single rate JSON file from GCS into the boe_base_rates table."""
    settings = settings or get_settings()
    table_id = f"{settings.gcp_project_id}.{settings.bq_raw_dataset}.boe_base_rates"
    load_ndjson_to_bq(gcs_uri=gcs_uri, table_id=table_id, schema=BOE_RATES_SCHEMA, settings=settings)
    return table_id


def load_gilt_yields(gcs_uri: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    table_id = f"{settings.gcp_project_id}.{settings.bq_raw_dataset}.gilt_yields"
    load_ndjson_to_bq(gcs_uri=gcs_uri, table_id=table_id, schema=GILT_YIELDS_SCHEMA, settings=settings)
    return table_id
