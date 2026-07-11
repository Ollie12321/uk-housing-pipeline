#!/usr/bin/env python3
"""Run Land Registry extract + BigQuery load in one step."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extract.land_registry import extract_land_registry
from load.bq_loader import load_land_registry

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    gcs_uri = extract_land_registry()
    table_id = load_land_registry(gcs_uri)
    print(f"Loaded into {table_id}")


if __name__ == "__main__":
    main()
