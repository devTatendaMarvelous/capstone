"""Execute the consolidated master notebook smartcrop_master.ipynb.

Checks environment dependencies, data files, and reproducibility settings before execution.

Usage:
    python data-science/scripts/execute_master_notebook.py [--timeout 300] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat


def find_data_science_dir() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "data-science").is_dir():
        return cwd / "data-science"
    if (cwd / "src" / "data" / "schema.py").is_file():
        return cwd
    for parent in cwd.parents:
        if (parent / "data-science" / "src" / "data" / "schema.py").is_file():
            return parent / "data-science"
    raise FileNotFoundError("Could not locate the data-science directory.")


def preflight_checks(ds_root: Path) -> None:
    """Validate prerequisites before executing the master notebook."""
    print("Running pre-flight checks...")

    # Check required data files
    required_data_files = [
        ds_root / "data" / "raw" / "batch_a_farm_observations.csv",
        ds_root / "data" / "raw" / "batch_b_farm_observations.xlsx",
        ds_root / "data" / "external" / "source_catalogue.csv",
    ]
    missing_data = [str(f) for f in required_data_files if not f.is_file()]
    if missing_data:
        raise FileNotFoundError(
            f"Pre-flight failed: Missing required raw data files: {missing_data}. "
            "Please ensure raw data batches exist before executing the pipeline."
        )
    print("  [✓] Raw data files verified.")

    # Check Python dependencies
    try:
        import joblib
        import matplotlib
        import numpy
        import openpyxl
        import pandas
        import sklearn
    except ImportError as exc:
        raise ImportError(f"Pre-flight failed: Missing required Python package: {exc}") from exc
    print("  [✓] Python dependencies verified (pandas, numpy, scikit-learn, joblib, matplotlib, openpyxl).")

    # Check master notebook exists
    master_path = ds_root / "notebooks" / "smartcrop_master.ipynb"
    if not master_path.is_file():
        raise FileNotFoundError(
            f"Pre-flight failed: Master notebook not found at {master_path}. "
            "Run python data-science/scripts/consolidate_notebooks.py first."
        )
    print("  [✓] Master notebook smartcrop_master.ipynb found.")


def execute_master_notebook(
    ds_root: Path | None = None,
    timeout: int = 300,
    output_path: Path | None = None,
) -> Path:
    ds_root = ds_root or find_data_science_dir()
    preflight_checks(ds_root)

    from nbclient import NotebookClient

    master_path = ds_root / "notebooks" / "smartcrop_master.ipynb"
    target_output = output_path or (ds_root / "reports" / "smartcrop_master_executed.ipynb")
    target_output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Reading master notebook from {master_path}...")
    with master_path.open("r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    print(f"Executing {len(nb.cells)} cells with timeout={timeout}s (working directory={ds_root})...")
    client = NotebookClient(
        nb,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(ds_root)}},
    )
    client.execute()

    print(f"Saving executed notebook to {target_output}...")
    with target_output.open("w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    print(f"Master notebook execution successful: {target_output}")
    return target_output


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the SmartCrop master notebook.")
    parser.add_argument("--timeout", type=int, default=300, help="Per-cell execution timeout in seconds.")
    parser.add_argument("--output", type=str, default="", help="Path for executed notebook output.")
    args = parser.parse_args()

    try:
        out = Path(args.output) if args.output else None
        execute_master_notebook(timeout=args.timeout, output_path=out)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
