"""
Pub/Sub subscriber that streams BoE rate change events into BigQuery.

Run as a long-lived process (e.g. inside a Cloud Run container or
a dedicated Airflow task with an external trigger):

    python -m streaming.pubsub_to_bq
"""

from __future__ import annotations

import json
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Any

from google.cloud import bigquery, pubsub_v1

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def _build_table_id(settings: Settings) -> str:
    return (
        f"{settings.gcp_project_id}."
        f"{settings.bq_raw_dataset}."
        "boe_rate_events_streaming"
    )


def _parse_message(message: pubsub_v1.subscriber.message.Message) -> dict[str, Any]:
    payload = json.loads(message.data.decode("utf-8"))
    return {
        "event_id": payload["event_id"],
        "effective_date": payload["effective_date"],
        "previous_rate": payload.get("previous_rate"),
        "new_rate": float(payload["new_rate"]),
        "published_at": payload.get("published_at", datetime.now(timezone.utc).isoformat()),
    }


def _stream_to_bq(client: bigquery.Client, table_id: str, row: dict) -> None:
    errors = client.insert_rows_json(table_id, [row])
    if errors:
        raise RuntimeError(f"BigQuery streaming insert errors: {errors}")
    logger.info("Streamed rate change event to BigQuery: %s", row)


def run_subscriber(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    bq_client = bigquery.Client(project=settings.gcp_project_id)
    table_id = _build_table_id(settings)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        settings.gcp_project_id,
        f"{settings.pubsub_rate_changes_topic}-sub",
    )

    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            row = _parse_message(message)
            _stream_to_bq(bq_client, table_id, row)
            message.ack()
        except Exception as exc:
            logger.error("Failed to process Pub/Sub message: %s", exc)
            message.nack()

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logger.info("Listening for rate change events on %s …", subscription_path)

    def _shutdown(signum, frame):
        logger.info("Shutting down Pub/Sub subscriber")
        streaming_pull_future.cancel()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    with subscriber:
        streaming_pull_future.result()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_subscriber()
