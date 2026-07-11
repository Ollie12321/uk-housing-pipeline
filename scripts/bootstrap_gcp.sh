#!/usr/bin/env bash
# =============================================================================
# bootstrap_gcp.sh
#
# One-time GCP setup: creates a project (optional), enables APIs,
# creates a service account, and downloads the JSON key.
#
# Usage:
#   chmod +x scripts/bootstrap_gcp.sh
#   ./scripts/bootstrap_gcp.sh
#
# Prerequisites:
#   - gcloud CLI installed: https://cloud.google.com/sdk/docs/install
#   - You are authenticated: gcloud auth login
# =============================================================================
set -euo pipefail

# ── Config — edit these ────────────────────────────────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-uk-housing-pipeline-$(date +%s | tail -c 5)}"
REGION="${GCP_REGION:-europe-west2}"
SA_NAME="uk-housing-pipeline"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_PATH="secrets/gcp-sa-key.json"
BILLING_ACCOUNT=""   # Optional: set your billing account ID (gcloud billing accounts list)
# ──────────────────────────────────────────────────────────────────────────────

echo ""
echo "========================================="
echo "  UK Housing Pipeline — GCP Bootstrap"
echo "========================================="
echo "Project ID : $PROJECT_ID"
echo "Region     : $REGION"
echo ""

# ── Step 1: Create project (skip if it already exists) ────────────────────────
if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
  echo "[1/6] Project $PROJECT_ID already exists — skipping creation"
else
  echo "[1/6] Creating project $PROJECT_ID …"
  gcloud projects create "$PROJECT_ID" --name="UK Housing Pipeline"

  if [[ -n "$BILLING_ACCOUNT" ]]; then
    gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
    echo "      Billing account linked."
  else
    echo ""
    echo "  ⚠️  No billing account set. Go to:"
    echo "      https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    echo "  and link a billing account before continuing."
    echo ""
    read -p "  Press ENTER once billing is linked, or Ctrl+C to abort …"
  fi
fi

gcloud config set project "$PROJECT_ID"

# ── Step 2: Enable required APIs ──────────────────────────────────────────────
echo "[2/6] Enabling APIs (this takes ~60 seconds) …"
gcloud services enable \
  bigquery.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project="$PROJECT_ID"
echo "      APIs enabled."

# ── Step 3: Create service account ────────────────────────────────────────────
echo "[3/6] Creating service account $SA_EMAIL …"
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
  echo "      Service account already exists — skipping."
else
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="UK Housing Pipeline" \
    --project="$PROJECT_ID"
fi

# ── Step 4: Grant IAM roles ────────────────────────────────────────────────────
echo "[4/6] Granting IAM roles …"
for ROLE in \
  roles/bigquery.dataEditor \
  roles/bigquery.jobUser \
  roles/storage.objectAdmin \
  roles/pubsub.publisher \
  roles/pubsub.subscriber; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="$ROLE" \
      --condition=None \
      --quiet
done
echo "      Roles granted."

# ── Step 5: Download service account key ──────────────────────────────────────
echo "[5/6] Downloading service account key to $KEY_PATH …"
mkdir -p secrets
gcloud iam service-accounts keys create "$KEY_PATH" \
  --iam-account="$SA_EMAIL" \
  --project="$PROJECT_ID"
echo "      Key saved."

# ── Step 6: Write .env ────────────────────────────────────────────────────────
echo "[6/6] Writing .env …"
BUCKET_NAME="uk-housing-raw-${PROJECT_ID}"
cat > .env <<EOF
GCP_PROJECT_ID=${PROJECT_ID}
GCP_REGION=${REGION}
GCS_BUCKET=${BUCKET_NAME}
BQ_RAW_DATASET=raw
BQ_STAGING_DATASET=staging
BQ_MARTS_DATASET=marts
PUBSUB_RATE_CHANGES_TOPIC=boe-rate-changes
GOOGLE_APPLICATION_CREDENTIALS=./secrets/gcp-sa-key.json
LAND_REGISTRY_YEAR=2025
EOF

# Also write terraform.tfvars
cat > terraform/terraform.tfvars <<EOF
project_id  = "${PROJECT_ID}"
region      = "${REGION}"
bucket_name = "${BUCKET_NAME}"
EOF

echo ""
echo "========================================="
echo "  Bootstrap complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. cd terraform && terraform init && terraform apply"
echo "  2. python -m venv .venv && source .venv/bin/activate"
echo "  3. pip install -r requirements.txt"
echo "  4. python scripts/run_full_pipeline.py"
echo ""
echo "Estimated GCP cost for this project: < £5/month"
echo "(BigQuery free tier: 10 GB storage, 1 TB queries/month)"
echo ""
