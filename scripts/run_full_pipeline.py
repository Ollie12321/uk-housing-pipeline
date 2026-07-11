#!/usr/bin/env python3
"""
Run the complete pipeline end-to-end:
  1. Land Registry CSV  → GCS → BigQuery
  2. BoE base rates     → GCS → BigQuery  (+ Pub/Sub if rate changed)
  3. Gilt yields        → GCS → BigQuery
  4. dbt run + test     (all models)

Usage:
    export $(grep -v '^#' .env | xargs)
    python scripts/run_full_pipeline.py

    # Or skip sources you don't want to reload:
    python scripts/run_full_pipeline.py --skip-land-registry
    python scripts/run_full_pipeline.py --only-dbt
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
DBT_DIR = str(ROOT / "dbt")


def _step(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def _elapsed(start: float) -> str:
    secs = int(time.time() - start)
    return f"{secs//60}m {secs%60}s"


def run_land_registry() -> None:
    _step("1/4  Land Registry → GCS → BigQuery")
    from extract.land_registry import extract_land_registry
    from load.bq_loader import load_land_registry

    t = time.time()
    log.info("Downloading Land Registry CSV (~150 MB) …")
    gcs_uri = extract_land_registry()
    log.info("Uploading to BigQuery …")
    table_id = load_land_registry(gcs_uri)
    log.info("Done in %s → %s", _elapsed(t), table_id)


def run_boe_rates() -> None:
    _step("2/4  BoE base rates → GCS → BigQuery")
    from extract.boe_rates import extract_boe_rates
    from load.bq_loader import load_boe_rates

    t = time.time()
    result = extract_boe_rates()
    table_id = load_boe_rates(result["gcs_uri"])
    changed = result["rate_changed"]
    log.info(
        "Done in %s → %s  (rate_changed=%s, current=%.2f%%)",
        _elapsed(t), table_id, changed, result["current"]["base_rate"],
    )


def run_gilt_yields() -> None:
    _step("3/4  Gilt yields → GCS → BigQuery")
    from extract.gilt_yields import extract_gilt_yields
    from load.bq_loader import load_gilt_yields

    t = time.time()
    gcs_uri = extract_gilt_yields()
    table_id = load_gilt_yields(gcs_uri)
    log.info("Done in %s → %s", _elapsed(t), table_id)


def run_dbt() -> None:
    _step("4/4  dbt run + test (all models)")
    env = {**os.environ, "GCP_PROJECT_ID": os.environ["GCP_PROJECT_ID"]}
    dbt_base = ["dbt", "--project-dir", DBT_DIR, "--profiles-dir", DBT_DIR]

    t = time.time()
    log.info("Installing dbt packages …")
    subprocess.run([*dbt_base, "deps"], check=True, env=env)

    log.info("Running all models …")
    subprocess.run([*dbt_base, "run"], check=True, env=env)

    log.info("Running all tests …")
    subprocess.run([*dbt_base, "test"], check=True, env=env)

    log.info("Generating docs …")
    subprocess.run([*dbt_base, "docs", "generate"], check=True, env=env)

    log.info("dbt complete in %s", _elapsed(t))
    print("\n  To view dbt docs locally:")
    print(f"    cd dbt && dbt docs serve")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full UK housing pipeline")
    parser.add_argument("--skip-land-registry", action="store_true")
    parser.add_argument("--skip-boe", action="store_true")
    parser.add_argument("--skip-gilts", action="store_true")
    parser.add_argument("--only-dbt", action="store_true")
    args = parser.parse_args()

    overall = time.time()

    if not args.only_dbt:
        if not args.skip_land_registry:
            run_land_registry()
        if not args.skip_boe:
            run_boe_rates()
        if not args.skip_gilts:
            run_gilt_yields()

    run_dbt()

    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {_elapsed(overall)}")
    print(f"{'='*60}")
    print("\nNext: open Looker Studio and connect to BigQuery")
    print("See docs/looker_studio_setup.md for the exact dashboard config.")
    print()


if __name__ == "__main__":
    main()
