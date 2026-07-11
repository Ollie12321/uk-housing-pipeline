"""Download HM Land Registry Price Paid Data and upload to GCS."""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from google.cloud import storage

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

LAND_REGISTRY_COLUMNS = [
    "transaction_id",
    "price",
    "transaction_date",
    "postcode",
    "property_type",
    "old_new",
    "duration",
    "paon",
    "saon",
    "street",
    "locality",
    "town_city",
    "district",
    "county",
    "ppd_category",
    "record_status",
]


def build_download_url(settings: Settings, year: int | None = None) -> str:
    target_year = year or settings.land_registry_year
    return f"{settings.land_registry_base_url}/pp-{target_year}.csv"


def download_land_registry_csv(
    settings: Settings | None = None,
    year: int | None = None,
    dest_dir: Path | None = None,
) -> Path:
    settings = settings or get_settings()
    url = build_download_url(settings, year)
    target_year = year or settings.land_registry_year

    output_dir = dest_dir or Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = output_dir / f"pp-{target_year}.csv"

    logger.info("Downloading Land Registry data from %s", url)
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with local_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)

    logger.info("Saved %s (%.1f MB)", local_path, local_path.stat().st_size / 1e6)
    return local_path


def upload_to_gcs(
    local_path: Path,
    settings: Settings | None = None,
    year: int | None = None,
) -> str:
    settings = settings or get_settings()
    target_year = year or settings.land_registry_year
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    blob_name = f"land_registry/year={target_year}/run_date={run_date}/{local_path.name}"
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(blob_name)

    logger.info("Uploading to gs://%s/%s", settings.gcs_bucket, blob_name)
    blob.upload_from_filename(str(local_path))

    gcs_uri = f"gs://{settings.gcs_bucket}/{blob_name}"
    logger.info("Upload complete: %s", gcs_uri)
    return gcs_uri


def extract_land_registry(
    settings: Settings | None = None,
    year: int | None = None,
) -> str:
    settings = settings or get_settings()
    with tempfile.TemporaryDirectory() as tmp:
        local_path = download_land_registry_csv(settings, year, Path(tmp))
        return upload_to_gcs(local_path, settings, year)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(extract_land_registry())
