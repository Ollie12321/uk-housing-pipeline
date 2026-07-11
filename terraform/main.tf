terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "raw_data" {
  name                        = var.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_bigquery_dataset" "raw" {
  dataset_id = var.raw_dataset_id
  location   = var.region
}

resource "google_bigquery_dataset" "staging" {
  dataset_id = var.staging_dataset_id
  location   = var.region
}

resource "google_bigquery_dataset" "marts" {
  dataset_id = var.marts_dataset_id
  location   = var.region
}

resource "google_bigquery_table" "land_registry_transactions" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "land_registry_transactions"
  deletion_protection = false

  time_partitioning {
    type  = "MONTH"
    field = "transaction_date"
  }

  clustering = ["county", "property_type"]

  schema = jsonencode([
    { name = "transaction_id", type = "STRING", mode = "NULLABLE" },
    { name = "price", type = "INTEGER", mode = "NULLABLE" },
    { name = "transaction_date", type = "DATE", mode = "NULLABLE" },
    { name = "postcode", type = "STRING", mode = "NULLABLE" },
    { name = "property_type", type = "STRING", mode = "NULLABLE" },
    { name = "old_new", type = "STRING", mode = "NULLABLE" },
    { name = "duration", type = "STRING", mode = "NULLABLE" },
    { name = "paon", type = "STRING", mode = "NULLABLE" },
    { name = "saon", type = "STRING", mode = "NULLABLE" },
    { name = "street", type = "STRING", mode = "NULLABLE" },
    { name = "locality", type = "STRING", mode = "NULLABLE" },
    { name = "town_city", type = "STRING", mode = "NULLABLE" },
    { name = "district", type = "STRING", mode = "NULLABLE" },
    { name = "county", type = "STRING", mode = "NULLABLE" },
    { name = "ppd_category", type = "STRING", mode = "NULLABLE" },
    { name = "record_status", type = "STRING", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "boe_base_rates" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "boe_base_rates"
  deletion_protection = false

  clustering = ["effective_date"]

  schema = jsonencode([
    { name = "effective_date", type = "DATE", mode = "REQUIRED" },
    { name = "base_rate", type = "FLOAT64", mode = "REQUIRED" },
    { name = "source", type = "STRING", mode = "NULLABLE" },
    { name = "loaded_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "gilt_yields" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "gilt_yields"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "date"
  }

  schema = jsonencode([
    { name = "date", type = "DATE", mode = "REQUIRED" },
    { name = "yield_pct", type = "FLOAT64", mode = "NULLABLE" },
    { name = "ticker", type = "STRING", mode = "NULLABLE" },
    { name = "loaded_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

resource "google_bigquery_table" "boe_rate_events_streaming" {
  dataset_id          = google_bigquery_dataset.raw.dataset_id
  table_id            = "boe_rate_events_streaming"
  deletion_protection = false

  schema = jsonencode([
    { name = "event_id", type = "STRING", mode = "REQUIRED" },
    { name = "effective_date", type = "DATE", mode = "REQUIRED" },
    { name = "previous_rate", type = "FLOAT64", mode = "NULLABLE" },
    { name = "new_rate", type = "FLOAT64", mode = "REQUIRED" },
    { name = "published_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_pubsub_topic" "rate_changes" {
  name = var.pubsub_topic_name
}

resource "google_pubsub_subscription" "rate_changes_bq" {
  name  = "${var.pubsub_topic_name}-sub"
  topic = google_pubsub_topic.rate_changes.name

  ack_deadline_seconds = 60

  expiration_policy {
    ttl = ""
  }
}
