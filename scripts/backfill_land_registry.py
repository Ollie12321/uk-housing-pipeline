#!/usr/bin/env python3
"""Backfill Land Registry data for multiple years into BigQuery.

Usage:
    python scripts/backfill_land_registry.py          # loads 2020-2024
    python scripts/backfill_land_registry.py 2018 2024 # custom range
"""
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
logger = logging.getLogger(__name__)


def backfill(start_year: int = 2020, end_year: int = 2024) -> None:
    years = list(range(start_year, end_year + 1))
    logger.info("Backfilling Land Registry data for years: %s", years)

    for year in years:
        logger.info("━━━ Year %s ━━━", year)
        try:
            gcs_uri = extract_land_registry(year=year)
            table_id = load_land_registry(gcs_uri)
            logger.info("Year %s loaded into %s", year, table_id)
        except Exception as exc:
            logger.error("Year %s FAILED: %s", year, exc)
            raise

    logger.info("Backfill complete for %s years.", len(years))


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2:
        backfill(int(args[0]), int(args[1]))
    elif len(args) == 0:
        backfill()
    else:
        print("Usage: backfill_land_registry.py [start_year end_year]")
        sys.exit(1)
