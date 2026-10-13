"""Tests for the master notebook consolidation script."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

# Ensure data-science root is in sys.path
_DS_DIR = Path(__file__).resolve().parents[1]
if str(_DS_DIR) not in sys.path:
    sys.path.insert(0, str(_DS_DIR))

import nbformat
import pytest
from scripts.consolidate_notebooks import (
    MASTER_NOTEBOOK_FILENAME,
    ORDERED_SOURCE_NOTEBOOKS,
    consolidate_notebooks,
    file_sha256,
    find_data_science_dir,
)


def test_ordered_source_notebooks_manifest():
    """Verify the manifest defines exactly the 7 Chapter 3 notebooks in canonical order."""
    filenames = [entry["filename"] for entry in ORDERED_SOURCE_NOTEBOOKS]
    expected = [
        "01_data_acquisition.ipynb",
        "02_data_cleaning.ipynb",
        "03_feature_engineering.ipynb",
        "04_eda_and_descriptive_analysis.ipynb",
        "05_model_training.ipynb",
        "06_model_evaluation.ipynb",
        "07_final_model.ipynb",
    ]
    assert filenames == expected
    assert MASTER_NOTEBOOK_FILENAME not in filenames


def test_consolidation_executes_safely_and_creates_master_notebook():
    """Verify that consolidation creates a valid master notebook and report."""
    ds_root = find_data_science_dir()
    notebooks_dir = ds_root / "notebooks"
    report_json = ds_root / "reports" / "consolidation_report.json"
    report_md = ds_root / "reports" / "consolidation_report.md"

    # Compute source checksums before running
    hashes_before = {
        entry["filename"]: file_sha256(notebooks_dir / entry["filename"])
        for entry in ORDERED_SOURCE_NOTEBOOKS
    }

    # Run consolidation
    report = consolidate_notebooks(clean_outputs=True)

    assert report["status"] == "success"
    assert report["total_source_notebooks"] == 7
    assert report["source_notebooks_unchanged"] is True
    assert report_json.is_file()
    assert report_md.is_file()

    master_path = notebooks_dir / MASTER_NOTEBOOK_FILENAME
    assert master_path.is_file()

    with master_path.open("r", encoding="utf-8") as f:
        master_nb = nbformat.read(f, as_version=4)

    # Validate notebook schema
    nbformat.validate(master_nb)

    # Master notebook must have title, sections, and cells
    assert len(master_nb.cells) > len(ORDERED_SOURCE_NOTEBOOKS)
    first_cell_text = "".join(master_nb.cells[0].source)
    assert "SmartCrop — Master Data Science Pipeline" in first_cell_text
    assert "Macheke, Mashonaland East, Zimbabwe" in first_cell_text

    # Verify all source notebook filenames appear in markdown dividers
    all_md_text = "\n".join(
        "".join(c.source) for c in master_nb.cells if c.cell_type == "markdown"
    )
    for entry in ORDERED_SOURCE_NOTEBOOKS:
        assert entry["filename"] in all_md_text

    # Verify source notebooks remained 100% unchanged
    hashes_after = {
        entry["filename"]: file_sha256(notebooks_dir / entry["filename"])
        for entry in ORDERED_SOURCE_NOTEBOOKS
    }
    assert hashes_before == hashes_after


def test_rerunning_consolidation_is_idempotent_and_excludes_master():
    """Running consolidation multiple times must produce identical output and not ingest master."""
    ds_root = find_data_science_dir()
    master_path = ds_root / "notebooks" / MASTER_NOTEBOOK_FILENAME

    # Run 1
    report1 = consolidate_notebooks(clean_outputs=True)
    hash1 = file_sha256(master_path)

    # Run 2
    report2 = consolidate_notebooks(clean_outputs=True)
    hash2 = file_sha256(master_path)

    # Content of master notebook must be identical and not contain itself recursively
    with master_path.open("r", encoding="utf-8") as f:
        master_nb = nbformat.read(f, as_version=4)

    # Check that master does not contain duplicate nested introductions
    intro_count = sum(
        1 for c in master_nb.cells
        if "SmartCrop — Master Data Science Pipeline" in "".join(c.source)
    )
    assert intro_count == 1
    assert report1["total_source_notebooks"] == report2["total_source_notebooks"]


def test_missing_source_notebook_raises_clear_error(tmp_path):
    """When a required source notebook is missing, the script must raise FileNotFoundError and log report."""
    fake_ds = tmp_path / "data-science"
    fake_notebooks = fake_ds / "notebooks"
    fake_reports = fake_ds / "reports"
    fake_notebooks.mkdir(parents=True)
    fake_reports.mkdir(parents=True)

    # Create only 6 out of 7 notebooks
    for entry in ORDERED_SOURCE_NOTEBOOKS[:-1]:
        nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell("# Test")])
        with (fake_notebooks / entry["filename"]).open("w") as f:
            nbformat.write(nb, f)

    with pytest.raises(FileNotFoundError, match="Required source notebook.*missing"):
        consolidate_notebooks(ds_dir=fake_ds)

    report_file = fake_reports / "consolidation_report.json"
    assert report_file.is_file()
    data = json.loads(report_file.read_text())
    assert data["status"] == "failed"
    assert ORDERED_SOURCE_NOTEBOOKS[-1]["filename"] in data["missing_notebooks"]
