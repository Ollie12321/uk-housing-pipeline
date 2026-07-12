#!/usr/bin/env python3
"""Load the full BoE rate history into BigQuery from the hardcoded RATE_HISTORY table.

This is a one-time backfill. The daily extract only records the *current* rate;
this script seeds the raw table with every rate change since 1997.
"""
from __future__ import annotations

import json
import logging
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from google.cloud import bigquery, storage
from config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RATE_HISTORY = [
    ("1997-06-06", 6.50), ("1997-07-10", 6.75), ("1997-08-07", 7.00),
    ("1997-11-06", 7.25), ("1998-06-04", 7.50), ("1998-10-08", 7.25),
    ("1998-11-05", 6.75), ("1998-12-10", 6.25), ("1999-01-07", 6.00),
    ("1999-02-04", 5.50), ("1999-04-08", 5.25), ("1999-06-10", 5.00),
    ("1999-09-08", 5.25), ("2000-02-10", 6.00), ("2001-02-08", 5.75),
    ("2001-04-05", 5.50), ("2001-05-10", 5.25), ("2001-08-02", 5.00),
    ("2001-09-18", 4.75), ("2001-10-04", 4.50), ("2001-11-08", 4.00),
    ("2002-11-07", 3.75), ("2003-02-06", 3.75), ("2003-07-10", 3.50),
    ("2004-02-05", 4.00), ("2004-05-06", 4.25), ("2004-06-10", 4.50),
    ("2004-08-05", 4.75), ("2004-11-04", 4.75), ("2005-08-04", 4.50),
    ("2006-08-03", 4.75), ("2006-11-09", 5.00), ("2007-01-11", 5.25),
    ("2007-05-10", 5.50), ("2007-07-05", 5.75), ("2007-12-06", 5.50),
    ("2008-02-07", 5.25), ("2008-04-10", 5.00), ("2008-10-08", 4.50),
    ("2008-11-06", 3.00), ("2008-12-04", 2.00), ("2009-01-08", 1.50),
    ("2009-02-05", 1.00), ("2009-03-05", 0.50), ("2016-08-04", 0.25),
    ("2017-11-02", 0.50), ("2018-08-02", 0.75), ("2020-03-11", 0.25),
    ("2020-03-19", 0.10), ("2021-12-16", 0.25), ("2022-02-03", 0.50),
    ("2022-03-17", 0.75), ("2022-05-05", 1.00), ("2022-06-16", 1.25),
    ("2022-08-04", 1.75), ("2022-09-22", 2.25), ("2022-11-03", 3.00),
    ("2022-12-15", 3.50), ("2023-02-02", 4.00), ("2023-03-23", 4.25),
    ("2023-05-11", 4.50), ("2023-06-22", 5.00), ("2023-08-03", 5.25),
    ("2024-08-01", 5.00), ("2024-11-07", 4.75), ("2025-02-06", 4.50),
    ("2025-05-08", 4.25), ("2025-08-07", 4.00), ("2025-12-18", 3.75),
]


def main() -> None:
    settings = get_settings()
    loaded_at = datetime.now(timezone.utc).isoformat()

    records = [
        {"effective_date": date, "base_rate": rate, "source": "bankofengland.co.uk", "loaded_at": loaded_at}
        for date, rate in RATE_HISTORY
    ]
    logger.info("Preparing %d rate records from 1997 to 2025", len(records))

    # Write NDJSON to GCS
    ndjson = "\n".join(json.dumps(r) for r in records)
    blob_name = "boe_rates/backfill/boe_rate_history.json"
    gcs_client = storage.Client(project=settings.gcp_project_id)
    bucket = gcs_client.bucket(settings.gcs_bucket)
    bucket.blob(blob_name).upload_from_string(ndjson, content_type="application/json")
    gcs_uri = f"gs://{settings.gcs_bucket}/{blob_name}"
    logger.info("Uploaded to %s", gcs_uri)

    # Load into BigQuery — WRITE_TRUNCATE to replace the single-row table
    bq = bigquery.Client(project=settings.gcp_project_id)
    table_id = f"{settings.gcp_project_id}.{settings.bq_raw_dataset}.boe_base_rates"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("effective_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("base_rate", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("source", "STRING"),
            bigquery.SchemaField("loaded_at", "TIMESTAMP"),
        ],
        autodetect=False,
    )
    job = bq.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    job.result()
    table = bq.get_table(table_id)
    logger.info("Loaded %d rows into %s", table.num_rows, table_id)


if __name__ == "__main__":
    main()
