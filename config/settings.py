import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    gcp_project_id: str
    gcp_region: str
    gcs_bucket: str
    bq_raw_dataset: str
    bq_staging_dataset: str
    bq_marts_dataset: str
    pubsub_rate_changes_topic: str
    land_registry_year: int

    @property
    def land_registry_base_url(self) -> str:
        return "https://price-paid-data.publicdata.landregistry.gov.uk"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        gcp_project_id=os.environ["GCP_PROJECT_ID"],
        gcp_region=os.environ.get("GCP_REGION", "europe-west2"),
        gcs_bucket=os.environ["GCS_BUCKET"],
        bq_raw_dataset=os.environ.get("BQ_RAW_DATASET", "raw"),
        bq_staging_dataset=os.environ.get("BQ_STAGING_DATASET", "staging"),
        bq_marts_dataset=os.environ.get("BQ_MARTS_DATASET", "marts"),
        pubsub_rate_changes_topic=os.environ.get(
            "PUBSUB_RATE_CHANGES_TOPIC", "boe-rate-changes"
        ),
        land_registry_year=int(os.environ.get("LAND_REGISTRY_YEAR", "2025")),
    )
