"""Consolidate the Chapter 3 data-science notebooks into a single master notebook.

Usage from repository root:
    python data-science/scripts/consolidate_notebooks.py

Usage from data-science directory:
    python scripts/consolidate_notebooks.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

# Explicit canonical execution order matching Chapter 3 methodology
ORDERED_SOURCE_NOTEBOOKS: list[dict[str, str]] = [
    {
        "filename": "01_data_acquisition.ipynb",
        "title": "Part 1: Data Acquisition and Understanding",
        "chapter_section": "Data Acquisition & Understanding",
        "description": "Loads raw CSV/Excel observation batches and source catalogue, checks schema units and multisets, and creates the consolidated raw dataset.",
    },
    {
        "filename": "02_data_cleaning.ipynb",
        "title": "Part 2: Data Cleaning and Preparation",
        "chapter_section": "Data Cleaning & Preparation",
        "description": "Applies cleaning rules (deduplication, physical/plausible bounds blanking, dropping missing yield) and exports clean_dataset.csv.",
    },
    {
        "filename": "03_feature_engineering.ipynb",
        "title": "Part 3: Feature Engineering",
        "chapter_section": "Feature Engineering",
        "description": "Constructs the three engineered features (temperature_range_c, degrees_above_33_c, planting_delay_days) and writes the feature dictionary.",
    },
    {
        "filename": "04_eda_and_descriptive_analysis.ipynb",
        "title": "Part 4: Exploratory and Descriptive Analysis",
        "chapter_section": "Exploratory Data Analysis",
        "description": "Calculates descriptive statistics, generates distributions and correlation matrices, and saves figures to reports/figures/.",
    },
    {
        "filename": "05_model_training.ipynb",
        "title": "Part 5: Model Training and Comparison",
        "chapter_section": "Model Comparison",
        "description": "Performs temporal cross-validation, trains candidate regressors on historical seasons, and exports model_comparison.csv.",
    },
    {
        "filename": "06_model_evaluation.ipynb",
        "title": "Part 6: Model Evaluation and Diagnostics",
        "chapter_section": "Model Evaluation",
        "description": "Selects the best algorithm on validation R², evaluates performance on held-out test seasons, tests the R² >= 0.80 target, and computes permutation importance.",
    },
    {
        "filename": "07_final_model.ipynb",
        "title": "Part 7: Final Model and Deployment Preparation",
        "chapter_section": "Final Model & Deployment Preparation",
        "description": "Fits the final pipeline on training seasons, serializes smartcrop_model.joblib and model_metadata.json, and exports final reports.",
    },
]

MASTER_NOTEBOOK_FILENAME = "smartcrop_master.ipynb"


def find_data_science_dir() -> Path:
    """Resolve data-science directory whether run from repo root or data-science/."""
    cwd = Path.cwd().resolve()
    if (cwd / "data-science").is_dir():
        return cwd / "data-science"
    if (cwd / "src" / "data" / "schema.py").is_file():
        return cwd
    if (cwd.parent / "src" / "data" / "schema.py").is_file():
        return cwd.parent
    for parent in cwd.parents:
        if (parent / "data-science" / "src" / "data" / "schema.py").is_file():
            return parent / "data-science"
    raise FileNotFoundError("Could not locate the data-science directory.")


def file_sha256(path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_source_notebook(path: Path) -> nbformat.NotebookNode:
    """Read and validate the structure of a source notebook."""
    if not path.is_file():
        raise FileNotFoundError(f"Source notebook not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    nbformat.validate(nb)
    return nb


def create_master_intro_markdown() -> str:
    """Master title and provenance preamble for smartcrop_master.ipynb."""
    return (
        "# SmartCrop — Master Data Science Pipeline\n\n"
        "**Project:** SmartCrop Yield Prediction Model for Smallholder Farmers  \n"
        "**Location:** Macheke, Mashonaland East, Zimbabwe  \n"
        "**Crop:** Maize (*Zea mays*)  \n"
        "**Target Variable:** `yield_t_ha` (Grain yield in tonnes per hectare)  \n"
        "**Methodology:** Consolidates Chapter 3 research notebooks 01 through 07 in deterministic execution order.  \n"
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  \n\n"
        "> **Important Data Provenance & Ethics Notice:**  \n"
        "> Rows in `data/synthetic/` and `data/interim/consolidated_raw.csv` were created for software and model-development exercises. "
        "> They are **not a survey of Macheke farms** and must not be cited as ZIMSTAT, Agritex, NASA POWER, CHIRPS, or SoilGrids measurements. "
        "> The academic performance target used here is **test $R^2 \\ge 0.80$**, which is **not met** on the synthetic held-out seasons. "
        "> $R^2$ is the coefficient of determination for continuous yield, not classification accuracy. "
        "> Predictions generated by the saved model are estimates and not a guaranteed harvest.\n\n"
        "### Pipeline Overview\n"
        "1. **Part 1: Data Acquisition & Understanding** (`01_data_acquisition.ipynb`)\n"
        "2. **Part 2: Data Cleaning & Preparation** (`02_data_cleaning.ipynb`)\n"
        "3. **Part 3: Feature Engineering** (`03_feature_engineering.ipynb`)\n"
        "4. **Part 4: Exploratory & Descriptive Analysis** (`04_eda_and_descriptive_analysis.ipynb`)\n"
        "5. **Part 5: Model Training & Comparison** (`05_model_training.ipynb`)\n"
        "6. **Part 6: Model Evaluation & Diagnostics** (`06_model_evaluation.ipynb`)\n"
        "7. **Part 7: Final Model & Deployment** (`07_final_model.ipynb`)\n\n"
        "---\n"
    )


def consolidate_notebooks(
    ds_dir: Path | None = None,
    clean_outputs: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Consolidate source notebooks into master notebook with detailed reporting.

    Returns the consolidation report dictionary.
    """
    ds_root = ds_dir or find_data_science_dir()
    notebooks_dir = ds_root / "notebooks"
    output_path = notebooks_dir / MASTER_NOTEBOOK_FILENAME
    reports_dir = ds_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = reports_dir / "consolidation_report.json"
    report_md_path = reports_dir / "consolidation_report.md"

    # Step 1: Pre-check source notebooks and capture initial checksums
    missing_notebooks: list[str] = []
    initial_checksums: dict[str, str] = {}
    for entry in ORDERED_SOURCE_NOTEBOOKS:
        fname = entry["filename"]
        # Explicitly ensure the master notebook is not among source inputs
        if fname == MASTER_NOTEBOOK_FILENAME:
            continue
        src_path = notebooks_dir / fname
        if not src_path.is_file():
            missing_notebooks.append(fname)
        else:
            initial_checksums[fname] = file_sha256(src_path)

    if missing_notebooks:
        error_msg = f"Consolidation failed: Required source notebook(s) missing: {missing_notebooks}"
        report = {
            "status": "failed",
            "error": error_msg,
            "missing_notebooks": missing_notebooks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise FileNotFoundError(error_msg)

    # Step 2: Initialize master notebook
    master_cells: list[nbformat.NotebookNode] = []
    master_cells.append(new_markdown_cell(create_master_intro_markdown()))

    report_sources: list[dict[str, Any]] = []
    total_cells_included = 0
    total_cells_excluded = 0

    # Step 3: Iterate through source notebooks in configured order
    for idx, entry in enumerate(ORDERED_SOURCE_NOTEBOOKS, start=1):
        fname = entry["filename"]
        src_path = notebooks_dir / fname
        source_nb = validate_source_notebook(src_path)

        # Part section divider
        divider_text = (
            f"---\n"
            f"# {entry['title']}\n\n"
            f"**Chapter 3 Stage:** {entry['chapter_section']}  \n"
            f"**Original Source Notebook:** [`{fname}`]({fname})  \n"
            f"**Execution Order:** Step {idx} of {len(ORDERED_SOURCE_NOTEBOOKS)}  \n\n"
            f"{entry['description']}\n"
        )
        master_cells.append(new_markdown_cell(divider_text))

        included_count = 0
        excluded_count = 0
        excluded_details: list[dict[str, Any]] = []

        for cell_idx, cell in enumerate(source_nb.cells):
            source_content = cell.source.strip() if isinstance(cell.source, str) else "".join(cell.source).strip()

            # Rule: omit empty cells (0 characters)
            if not source_content:
                excluded_count += 1
                excluded_details.append({
                    "original_cell_index": cell_idx,
                    "cell_type": cell.cell_type,
                    "reason": "Empty cell (0 characters) omitted",
                })
                continue

            # Clone cell safely
            if cell.cell_type == "markdown":
                cloned = new_markdown_cell(source=cell.source, metadata=cell.metadata)
            elif cell.cell_type == "code":
                # Remove stale outputs by default to keep the notebook lean and reproducible
                outputs = [] if clean_outputs else cell.get("outputs", [])
                cloned = new_code_cell(
                    source=cell.source,
                    execution_count=None if clean_outputs else cell.get("execution_count"),
                    outputs=outputs,
                    metadata=cell.metadata,
                )
            else:
                cloned = nbformat.from_dict(cell)

            master_cells.append(cloned)
            included_count += 1

        total_cells_included += included_count
        total_cells_excluded += excluded_count

        report_sources.append({
            "order": idx,
            "filename": fname,
            "title": entry["title"],
            "chapter_section": entry["chapter_section"],
            "cells_read": len(source_nb.cells),
            "cells_included": included_count,
            "cells_excluded": excluded_count,
            "excluded_details": excluded_details,
            "sha256": initial_checksums[fname],
        })

    # Step 4: Add Appendix / Ethical Limitations cell at the end
    master_cells.append(
        new_markdown_cell(
            "---\n"
            "# Appendix: Reproducibility, Ethics, and Agronomic Limitations\n\n"
            "### Reproducibility Controls\n"
            "- Random seed: `RANDOM_SEED = 42` is fixed across data generation, temporal splitting, cross-validation, and permutation importance.\n"
            "- Preprocessing integrity: Median imputation is fit exclusively on the training season window inside the scikit-learn pipeline, preventing data leakage into validation/test splits.\n"
            "- Feature alignment: The 9 raw features and 3 engineered features match the exact operational production schema.\n\n"
            "### Agricultural and Methodological Disclaimers\n"
            "1. **Synthetic Training Baseline:** The baseline dataset contains synthetic observations. It is not an empirical agronomic survey of Macheke smallholder farms.\n"
            "2. **Non-Causal Feature Importance:** Permutation importance reflects statistical association inside the fitted model. It does not establish causal fertilizer responses.\n"
            "3. **Study Area Approximation:** Boundary coordinates represent an experimental study area bounding box around Macheke, not an official administrative boundary.\n"
            "4. **Production Model Advice:** Predictions must be accompanied by confidence limitations and should not be treated as guaranteed harvest yields."
        )
    )

    # Step 5: Construct master notebook object
    master_nb = new_notebook(cells=master_cells)
    master_nb.metadata = {
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12",
            "mimetype": "text/x-python",
            "codemirror_mode": {"name": "ipython", "version": 3},
            "pygments_lexer": "ipython3",
        },
        "smartcrop": {
            "consolidated": True,
            "source_notebook_count": len(ORDERED_SOURCE_NOTEBOOKS),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # Step 6: Validate master notebook structure
    nbformat.validate(master_nb)

    # Step 7: Save master notebook (unless dry run)
    if not dry_run:
        with output_path.open("w", encoding="utf-8") as f:
            nbformat.write(master_nb, f)

    # Step 8: Verify that source notebooks remain UNCHANGED
    post_checksums: dict[str, str] = {}
    tampered_notebooks: list[str] = []
    for entry in ORDERED_SOURCE_NOTEBOOKS:
        fname = entry["filename"]
        src_path = notebooks_dir / fname
        current_hash = file_sha256(src_path)
        post_checksums[fname] = current_hash
        if current_hash != initial_checksums[fname]:
            tampered_notebooks.append(fname)

    if tampered_notebooks:
        raise RuntimeError(
            f"Integrity check failed! Source notebook(s) modified during consolidation: {tampered_notebooks}"
        )

    # Step 9: Write Consolidation Report
    report: dict[str, Any] = {
        "status": "success",
        "output_path": str(output_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_source_notebooks": len(ORDERED_SOURCE_NOTEBOOKS),
        "total_cells_in_master": len(master_cells),
        "total_source_cells_included": total_cells_included,
        "total_source_cells_excluded": total_cells_excluded,
        "clean_outputs_applied": clean_outputs,
        "source_notebooks_unchanged": True,
        "missing_notebooks": [],
        "sources": report_sources,
    }

    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Format Markdown report
    md_lines = [
        "# SmartCrop Notebook Consolidation Report\n",
        f"**Date:** {report['generated_at']}  ",
        f"**Master Notebook:** `{output_path.name}`  ",
        f"**Master Path:** `{output_path}`  ",
        f"**Total Master Cells:** {len(master_cells)}  ",
        f"**Clean Outputs Applied:** {clean_outputs}  ",
        f"**Original Files Integrity:** Verified unchanged  \n",
        "## Included Source Notebooks in Execution Order\n",
        "| Step | Source Notebook | Stage | Cells In | Cells Excluded | Checksum (SHA256) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for s in report_sources:
        md_lines.append(
            f"| {s['order']} | `{s['filename']}` | {s['chapter_section']} | {s['cells_included']} | {s['cells_excluded']} | `{s['sha256'][:12]}...` |"
        )

    md_lines.append("\n## Excluded Cells Log\n")
    if total_cells_excluded == 0:
        md_lines.append("No cells were excluded. All source cells were preserved.")
    else:
        for s in report_sources:
            if s["cells_excluded"] > 0:
                md_lines.append(f"### `{s['filename']}` ({s['cells_excluded']} excluded)\n")
                for item in s["excluded_details"]:
                    md_lines.append(f"- Cell index {item['original_cell_index']} ({item['cell_type']}): {item['reason']}")
                md_lines.append("")

    report_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate SmartCrop source notebooks into master notebook.")
    parser.add_argument(
        "--keep-outputs",
        action="store_true",
        help="Keep stale execution outputs instead of stripping them (default: clean outputs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate source notebooks and generate report without writing master notebook.",
    )
    args = parser.parse_args()

    try:
        report = consolidate_notebooks(clean_outputs=not args.keep_outputs, dry_run=args.dry_run)
        print("Notebook consolidation complete:")
        print(f"  Master Notebook: {report['output_path']}")
        print(f"  Total Master Cells: {report['total_cells_in_master']}")
        print(f"  Sources Included: {report['total_source_notebooks']}")
        print(f"  Source Cells Included: {report['total_source_cells_included']}")
        print(f"  Source Cells Excluded: {report['total_source_cells_excluded']}")
        print(f"  Source Integrity: {'Verified unchanged' if report['source_notebooks_unchanged'] else 'FAILED'}")
        print(f"  Report JSON: data-science/reports/consolidation_report.json")
        print(f"  Report MD:   data-science/reports/consolidation_report.md")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
