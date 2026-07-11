variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for regional resources"
  type        = string
  default     = "europe-west2"
}

variable "bucket_name" {
  description = "GCS bucket for raw data"
  type        = string
}

variable "raw_dataset_id" {
  type    = string
  default = "raw"
}

variable "staging_dataset_id" {
  type    = string
  default = "staging"
}

variable "marts_dataset_id" {
  type    = string
  default = "marts"
}

variable "pubsub_topic_name" {
  type    = string
  default = "boe-rate-changes"
}
