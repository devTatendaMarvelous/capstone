"""HTTP downloads with cache, retry, timeout, and a request log."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from utils.config import data_dir, load_config
from utils.logging import get_logger

LOG = get_logger()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_log(row: dict) -> None:
    path = data_dir() / "logs" / "download_log.csv"
    frame = pd.DataFrame([row])
    frame.to_csv(path, mode="a", header=not path.exists(), index=False)


def fetch_bytes(url: str, dest: Path | None = None, data: bytes | None = None, force: bool = False) -> tuple[int, bytes]:
    """GET or POST a URL. A cached file is reused when dest already exists."""
    config = load_config()["requests"]
    dest = Path(dest) if dest else None
    if dest and dest.is_file() and dest.stat().st_size > 0 and not force:
        body = dest.read_bytes()
        LOG.info("cache hit %s", dest)
        _append_log(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "cache",
                "url": url,
                "status_code": 200,
                "file": str(dest),
                "bytes": len(body),
                "checksum": file_sha256(dest),
            }
        )
        return 200, body

    headers = {"User-Agent": config["user_agent"], "Accept": "*/*"}
    delay = 1.0
    last_error: Exception | None = None
    for attempt in range(1, int(config["retries"]) + 1):
        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=int(config["timeout_seconds"])) as response:
                body = response.read()
                status = response.status
            if dest:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(body)
            checksum = hashlib.sha256(body).hexdigest()
            _append_log(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "http",
                    "url": url,
                    "status_code": status,
                    "file": str(dest or ""),
                    "bytes": len(body),
                    "checksum": checksum,
                }
            )
            LOG.info("downloaded status=%s bytes=%s url=%s", status, len(body), url[:160])
            return status, body
        except urllib.error.HTTPError as exc:
            last_error = exc
            LOG.warning("HTTP %s on attempt %s for %s", exc.code, attempt, url[:160])
            if exc.code in {400, 401, 403, 404}:
                break
        except Exception as exc:  # noqa: BLE001 - logged and retried
            last_error = exc
            LOG.warning("download attempt %s failed for %s: %s", attempt, url[:160], exc)
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"Download failed for {url}: {last_error}")


def fetch_json(url: str, dest: Path | None = None, data: bytes | None = None, force: bool = False):
    status, body = fetch_bytes(url, dest, data=data, force=force)
    return status, json.loads(body.decode("utf-8"))
