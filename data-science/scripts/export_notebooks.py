"""Export executed notebooks to HTML. The model PDF is written by the research report.

PDF export of notebooks needs a LaTeX installation. This script writes HTML
for every notebook and leaves the model report PDF, which is built with
ReportLab and does not need LaTeX, in reports/final_model_report.pdf.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
EXPORT = ROOT / "reports" / "exported" / "notebooks"


def main() -> int:
    EXPORT.mkdir(parents=True, exist_ok=True)
    failures = 0
    for notebook in sorted(NOTEBOOKS.glob("*.ipynb")):
        command = [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "html",
            "--output-dir",
            str(EXPORT),
            str(notebook),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            failures += 1
    print(f"HTML notebooks: {EXPORT}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
