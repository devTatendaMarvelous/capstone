"""Look for a public Agritex or ministry table. Do not collect farmer identities."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pandas as pd

from utils.config import data_dir
from utils.downloads import fetch_bytes
from utils.logging import get_logger

LOG = get_logger()
PAGES = [
    "https://www.agriculture.gov.zw/",
    "https://zimstat.co.zw/",
]


def acquire_agritex() -> dict:
    raw_dir = data_dir() / "raw" / "agritex"
    raw_dir.mkdir(parents=True, exist_ok=True)
    notes = []
    for url in PAGES:
        try:
            _status, body = fetch_bytes(url, raw_dir / (re.sub(r"[^a-z0-9]+", "_", url)[:40] + ".html"), force=True)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{url} could not be downloaded: {exc}")
            continue
        text = body.decode("utf-8", errors="replace")
        if re.search(r"Macheke", text, re.I) and re.search(r"yield|maize", text, re.I):
            notes.append(f"{url} mentions Macheke near maize or yield text, but no structured table was extracted.")
        else:
            notes.append(f"{url} was reviewed. No public Macheke maize table was identified for ingestion.")
    note = {
        "source": "AGRITEX",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "ingestion_status": "reviewed_not_ingested",
        "records_ingested": 0,
        "notes": " ".join(notes) + " Personal farmer records were not scraped.",
    }
    pd.DataFrame([note]).to_csv(raw_dir / "review.csv", index=False)
    LOG.info("Agritex/ministry review: %s", note["ingestion_status"])
    return note
