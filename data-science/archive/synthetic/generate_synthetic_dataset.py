#!/usr/bin/env python3
"""Generate the labelled SmartCrop synthetic maize dataset.

Run from the data-science directory:

    python generate_synthetic_dataset.py

Optional arguments match the generator configuration:

    --number-of-records
    --number-of-seasons
    --random-seed
    --missing-rate
    --outlier-rate
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from data.synthetic import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
