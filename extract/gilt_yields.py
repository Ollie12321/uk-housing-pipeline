"""Download UK 10-year gilt yields via yfinance and upload to GCS."""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from google.cloud import storage

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# UK 10-year gilt benchmark ticker on Yahoo Finance
GILT_TICKER = "^TNX"  # fallback: GB10YT=RR or GBGB10YT=RR
UK_GILT_TICKER = "GB10YT=RR"


def _fetch_gilt_yields(lookback_days: int = 35) -> list[dict]:
    """
    Pull recent UK 10-year gilt yield data.

    Strategy:
    1. FRED IRLTLT01GBM156N — UK 10Y government bond yield, monthly (most reliable)
    2. Yahoo Finance ^TNX (US 10Y as a proxy when UK data unavailable)
    Returns list of {date, yield_pct, ticker} dicts.
    """
    loaded_at = datetime.now(timezone.utc).isoformat()

    # Primary: FRED monthly UK gilt yields
    try:
        resp = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRLTLT01GBM156N",
            timeout=15,
            headers={"User-Agent": "uk-housing-pipeline/1.0"},
        )
        if resp.status_code == 200:
            records = []
            lines = [l for l in resp.text.splitlines() if l.strip() and not l.startswith("observation")]
            for line in lines[-lookback_days:]:
                parts = line.split(",")
                if len(parts) == 2:
                    try:
                        date_str, yield_str = parts
                        yield_pct = float(yield_str.strip())
                        records.append({
                            "date": date_str.strip(),
                            "yield_pct": round(yield_pct, 4),
                            "ticker": "IRLTLT01GBM156N",
                            "loaded_at": loaded_at,
                        })
                    except ValueError:
                        continue
            if records:
                logger.info("Fetched %d UK gilt yield records from FRED", len(records))
                return records
    except Exception as exc:
        logger.warning("FRED gilt fetch failed (%s), falling back to yfinance", exc)

    # Fallback: yfinance (columns are multi-level in recent versions)
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=lookback_days)
    for ticker in ("^TNX",):
        try:
            data = yf.download(ticker, start=start.isoformat(), end=end.isoformat(),
                               progress=False, auto_adjust=True)
            if data.empty:
                continue
            # Flatten multi-level columns produced by recent yfinance versions
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            records = []
            for ts, row in data.iterrows():
                close = row.get("Close")
                if close is None or (hasattr(close, "__len__") and not isinstance(close, (int, float))):
                    continue
                records.append({
                    "date": ts.date().isoformat(),
                    "yield_pct": round(float(close), 4),
                    "ticker": ticker,
                    "loaded_at": loaded_at,
                })
            if records:
                logger.info("Fetched %d yield records from yfinance (%s)", len(records), ticker)
                return records
        except Exception as exc:
            logger.warning("yfinance ticker %s failed: %s", ticker, exc)

    raise RuntimeError("Could not fetch gilt yields from any source")


def _upload_to_gcs(records: list[dict], settings: Settings, run_date: str) -> str:
    ndjson = "\n".join(json.dumps(r) for r in records)
    blob_name = f"gilts/date={run_date}/gilt_yields.ndjson"
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(ndjson, content_type="application/x-ndjson")
    gcs_uri = f"gs://{settings.gcs_bucket}/{blob_name}"
    logger.info("Uploaded gilt yields to %s", gcs_uri)
    return gcs_uri


def extract_gilt_yields(
    settings: Settings | None = None,
    lookback_days: int = 5,
) -> str:
    settings = settings or get_settings()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = _fetch_gilt_yields(lookback_days)
    return _upload_to_gcs(records, settings, run_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(extract_gilt_yields())
