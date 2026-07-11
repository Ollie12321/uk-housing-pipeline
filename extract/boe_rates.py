"""Fetch Bank of England base rate, detect changes, and publish to Pub/Sub."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests
from google.cloud import pubsub_v1, storage

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# BoE public API — Statistical Interactive Database (IADB)
# Series code: IUDBEDR = Official Bank Rate
BOE_API_URL = (
    "https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp"
    "?Travel=NIxIRxSUx&FromSeries=1&ToSeries=50&DAT=RNG"
    "&FD=1&FM=Jan&FY=1994&TD=31&TM=Dec&TY={year}&VFD=Y&html.x=66&html.y=26"
    "&C=C5H&Filter=N"
)
BOE_JSON_API = (
    "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"
    "?CodeVer=new&xml.x=yes"
)
# Simpler endpoint using the public data API
BOE_DATA_API = "https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"
STATE_BLOB = "boe_rates/state/last_known_rate.json"


def _fetch_current_rate() -> dict:
    """
    Pull the current BoE base rate.

    Strategy:
    1. Try the FRED IUMABEDR series (BoE Bank Rate, monthly, FRED-hosted)
    2. Fall back to a maintained hardcoded table of rate change dates
    Returns dict with 'effective_date' and 'base_rate'.
    """
    # BoE rate change history (effective dates, chronological)
    # Source: bankofengland.co.uk — manually maintained fallback
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
        ("2025-05-08", 4.25),
    ]

    # Try FRED first for a machine-readable current value
    try:
        resp = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IUMABEDR",
            timeout=15,
            headers={"User-Agent": "uk-housing-pipeline/1.0"},
        )
        if resp.status_code == 200:
            lines = [l for l in resp.text.splitlines() if l.strip() and not l.startswith("observation")]
            for line in reversed(lines):
                parts = line.split(",")
                if len(parts) == 2:
                    try:
                        date_str, rate_str = parts
                        rate = float(rate_str.strip())
                        if rate > 0:
                            return {"effective_date": date_str.strip(), "base_rate": rate}
                    except ValueError:
                        continue
    except Exception as exc:
        logger.warning("FRED fetch failed (%s), using hardcoded history", exc)

    # Fall back to the hardcoded table — return the most recent entry
    latest_date, latest_rate = RATE_HISTORY[-1]
    logger.info("Using hardcoded rate table: %s%% effective %s", latest_rate, latest_date)
    return {"effective_date": latest_date, "base_rate": latest_rate}


def _load_state(client: storage.Client, bucket_name: str) -> Optional[dict]:
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(STATE_BLOB)
    if blob.exists():
        return json.loads(blob.download_as_text())
    return None


def _save_state(client: storage.Client, bucket_name: str, state: dict) -> None:
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(STATE_BLOB)
    blob.upload_from_string(json.dumps(state), content_type="application/json")


def _upload_rate_to_gcs(
    client: storage.Client, bucket_name: str, record: dict, run_date: str
) -> str:
    blob_name = f"boe_rates/date={run_date}/boe_base_rate.json"
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(record), content_type="application/json")
    return f"gs://{bucket_name}/{blob_name}"


def _publish_rate_change(
    settings: Settings, previous: Optional[float], current: dict
) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        settings.gcp_project_id, settings.pubsub_rate_changes_topic
    )
    event = {
        "event_id": str(uuid.uuid4()),
        "effective_date": current["effective_date"],
        "previous_rate": previous,
        "new_rate": current["base_rate"],
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    data = json.dumps(event).encode("utf-8")
    future = publisher.publish(topic_path, data)
    msg_id = future.result()
    logger.info(
        "Published rate change event to Pub/Sub (message_id=%s): %s -> %s",
        msg_id,
        previous,
        current["base_rate"],
    )


def extract_boe_rates(settings: Settings | None = None) -> dict:
    """
    Fetch the current BoE base rate, compare against stored state.
    - Always uploads the latest rate to GCS.
    - If the rate has changed, publishes an event to Pub/Sub.
    Returns a dict with 'gcs_uri', 'rate_changed', and 'current'.
    """
    settings = settings or get_settings()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    current = _fetch_current_rate()
    current["loaded_at"] = datetime.now(timezone.utc).isoformat()
    current["source"] = "bankofengland.co.uk"

    logger.info("BoE base rate: %s%% (effective %s)", current["base_rate"], current["effective_date"])

    gcs_client = storage.Client(project=settings.gcp_project_id)
    gcs_uri = _upload_rate_to_gcs(gcs_client, settings.gcs_bucket, current, run_date)

    last_state = _load_state(gcs_client, settings.gcs_bucket)
    rate_changed = last_state is None or last_state["base_rate"] != current["base_rate"]

    if rate_changed:
        previous_rate = last_state["base_rate"] if last_state else None
        logger.info(
            "Rate changed: %s -> %s — publishing Pub/Sub event",
            previous_rate,
            current["base_rate"],
        )
        _publish_rate_change(settings, previous_rate, current)
        _save_state(gcs_client, settings.gcs_bucket, current)
    else:
        logger.info("Rate unchanged (%s%%) — no Pub/Sub event", current["base_rate"])

    return {"gcs_uri": gcs_uri, "rate_changed": rate_changed, "current": current}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(extract_boe_rates())
