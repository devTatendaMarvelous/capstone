"""Look for a public ZIMSTAT agricultural table. Do not invent district yields."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

from utils.config import data_dir
from utils.downloads import fetch_bytes
from utils.logging import get_logger

LOG = get_logger()
HOME = "https://zimstat.co.zw/"


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)


def acquire_zimstat() -> dict:
    raw_dir = data_dir() / "raw" / "zimstat"
    raw_dir.mkdir(parents=True, exist_ok=True)
    note = {
        "source": "ZIMSTAT",
        "url": HOME,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "ingestion_status": "reviewed_not_ingested",
        "records_ingested": 0,
        "notes": "",
    }
    try:
        _status, body = fetch_bytes(HOME, raw_dir / "homepage.html", force=True)
    except Exception as exc:  # noqa: BLE001
        note["notes"] = f"Homepage could not be downloaded: {exc}"
        LOG.warning(note["notes"])
        _write(raw_dir, note)
        return note
    parser = _Links()
    parser.feed(body.decode("utf-8", errors="replace"))
    interesting = [
        href
        for href in parser.hrefs
        if re.search(r"agricultur|maize|crop|production|survey", href, re.I)
    ]
    (raw_dir / "candidate_links.txt").write_text("\n".join(interesting), encoding="utf-8")
    files = [href for href in interesting if re.search(r"\.(csv|xlsx|xls)(\?|$)", href, re.I)]
    if not files:
        note["notes"] = (
            "The public homepage was saved. No CSV or Excel agricultural table was linked "
            "from that page, so no ZIMSTAT measurements were ingested. District maize yield "
            "was not inferred from national figures."
        )
        LOG.info(note["notes"])
        _write(raw_dir, note)
        return note
    note["notes"] = "A tabular link was seen but not automatically treated as Macheke farm data: " + files[0]
    LOG.info(note["notes"])
    _write(raw_dir, note)
    return note


def _write(raw_dir: Path, note: dict) -> None:
    pd.DataFrame([note]).to_csv(raw_dir / "review.csv", index=False)
