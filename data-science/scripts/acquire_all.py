"""Download real SmartCrop sources. This script does not generate observations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acquisition.agritex import acquire_agritex
from acquisition.chirps import acquire_chirps
from acquisition.faostat import acquire_faostat
from acquisition.nasa_power import acquire_nasa_power
from acquisition.soilgrids import acquire_soilgrids
from acquisition.yield_sources import acquire_yield_tables
from acquisition.zimstat import acquire_zimstat
from utils.logging import get_logger

LOG = get_logger()


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire real SmartCrop source data.")
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "nasa", "chirps", "soilgrids", "faostat", "zimstat", "agritex"],
    )
    args = parser.parse_args()
    selected = args.source
    steps = []
    if selected in {"all", "nasa"}:
        steps.append(("nasa", acquire_nasa_power))
    if selected in {"all", "chirps"}:
        steps.append(("chirps", acquire_chirps))
    if selected in {"all", "soilgrids"}:
        steps.append(("soilgrids", acquire_soilgrids))
    if selected in {"all", "faostat"}:
        steps.append(("faostat", acquire_faostat))
    if selected in {"all", "zimstat"}:
        steps.append(("zimstat", acquire_zimstat))
    if selected in {"all", "agritex"}:
        steps.append(("agritex", acquire_agritex))
    failures = 0
    for name, function in steps:
        try:
            function()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            LOG.exception("%s acquisition failed: %s", name, exc)
    if selected == "all":
        try:
            acquire_yield_tables()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            LOG.exception("yield table build failed: %s", exc)
    LOG.info("Acquisition finished for %s with %s failures", selected, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
