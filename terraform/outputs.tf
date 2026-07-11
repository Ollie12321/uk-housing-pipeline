output "gcs_bucket_name" {
  value = google_storage_bucket.raw_data.name
}

output "raw_dataset_id" {
  value = google_bigquery_dataset.raw.dataset_id
}

output "staging_dataset_id" {
  value = google_bigquery_dataset.staging.dataset_id
}

output "marts_dataset_id" {
  value = google_bigquery_dataset.marts.dataset_id
}

output "pubsub_topic_name" {
  value = google_pubsub_topic.rate_changes.name
}

output "pipeline_service_account_email" {
  value = google_service_account.pipeline_sa.email
}
