"""Write the real-data notebooks. Run them after build_dataset.py."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"


def notebook(cells):
    book = new_notebook(cells=cells)
    book.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    return book


def write(name, cells):
    path = OUT / name
    nbformat.write(notebook(cells), path)
    print(path)


SETUP = """import sys
from pathlib import Path
ROOT = Path.cwd()
if not (ROOT / "src").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))
import pandas as pd
DATA = ROOT / "data"
"""

write(
    "01_real_data_acquisition.ipynb",
    [
        new_markdown_cell(
            "# 01 Real data acquisition\n\n"
            "Sources are downloaded, not simulated. A missing farm yield stays missing. "
            "The study-area polygon is an approximation around Macheke, not an official boundary."
        ),
        new_code_cell(SETUP + """
from utils.config import load_config
config = load_config(ROOT / "config" / "smartcrop_config.yaml")
print(config["study_area"]["boundary_status"])
print(config["season"]["assumption"])
catalogue = pd.read_csv(DATA / "metadata" / "source_catalogue.csv")
catalogue[["source_id", "ingestion_status", "records_ingested"]]
"""),
        new_code_cell("""
def read_if_present(path):
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()
nasa = read_if_present(DATA / "interim" / "nasa_power_daily.csv")
chirps = read_if_present(DATA / "interim" / "chirps_daily.csv")
soil = read_if_present(DATA / "processed" / "soilgrids_points.csv")
faostat = read_if_present(DATA / "processed" / "faostat_zimbabwe_maize.csv")
print("NASA POWER daily", len(nasa), "CHIRPS daily", len(chirps), "SoilGrids", len(soil), "FAOSTAT national years", len(faostat))
faostat.head(3)
"""),
    ],
)

write(
    "02_real_data_quality.ipynb",
    [
        new_markdown_cell(
            "# 02 Real data quality\n\n"
            "Flags are recorded. Rows are not deleted and missing yield is not imputed here."
        ),
        new_code_cell(SETUP + """
frame = pd.read_csv(DATA / "processed" / "capstone_dataset_real.csv")
print(frame["quality_flag"].value_counts(dropna=False))
print("missing yield", int(frame["yield_t_ha"].isna().sum()))
print("synthetic", int(frame["synthetic_record"].fillna(False).astype(bool).sum()))
print("latitude outside Zimbabwe", int((~frame["latitude"].between(-22.9, -15.5)).sum()))
pd.read_csv(DATA / "metadata" / "provenance.csv")
"""),
    ],
)

write(
    "03_real_data_integration.ipynb",
    [
        new_markdown_cell(
            "# 03 Real data integration\n\n"
            "Join order: seasonal CHIRPS rainfall and NASA weather on harvest year, "
            "then the SoilGrids point, then FAOSTAT national maize yield on year. "
            "The yield is not computed from the weather."
        ),
        new_code_cell(SETUP + """
nasa = pd.read_csv(DATA / "processed" / "nasa_power_seasonal.csv")
chirps = pd.read_csv(DATA / "processed" / "chirps_seasonal.csv")
final = pd.read_csv(DATA / "processed" / "capstone_dataset_real.csv")
print("NASA seasons", len(nasa), "CHIRPS seasons", len(chirps), "integrated rows", len(final))
print("rows with a real yield", int(final["yield_t_ha"].notna().sum()))
final[["year", "season", "geographic_level", "yield_geographic_level", "season_rainfall_mm", "avg_temperature_c", "yield_t_ha"]].head()
"""),
    ],
)

write(
    "04_real_data_eda.ipynb",
    [
        new_markdown_cell(
            "# 04 Real data EDA\n\n"
            "Rainfall and temperature describe the Macheke study-area grid. "
            "Yield, when plotted, is FAOSTAT national Zimbabwe maize yield. "
            "A correlation here is not a Macheke farm finding."
        ),
        new_code_cell(SETUP + """
frame = pd.read_csv(DATA / "processed" / "capstone_dataset_real.csv")
columns = ["season_rainfall_mm", "avg_temperature_c", "max_temperature_c", "min_temperature_c", "heat_stress_days", "yield_t_ha", "soil_ph"]
print(frame[columns].describe())
print(frame[columns].corr(numeric_only=True))
"""),
    ],
)

write(
    "05_real_model_metrics.ipynb",
    [
        new_markdown_cell(
            "# 05 Real-data model metrics\n\n"
            "Metrics are MAE, RMSE, and R² on later harvest years. "
            "R² is the coefficient of determination, not classification accuracy. "
            "The 0.80 R² target is a research threshold, not a claim that has already been met. "
            "If farm-level Macheke yields are absent, the fit below uses FAOSTAT national yield "
            "and must not be described as a farm-level model."
        ),
        new_code_cell(SETUP + """
from models.real_training import WARNING, train_from_real_dataset
print(WARNING)
model_frame = pd.read_csv(DATA / "processed" / "modelling_dataset.csv")
result = train_from_real_dataset(model_frame, ROOT / "reports" / "model_reports")
print("status", result["status"])
print("chosen", result.get("chosen_model"))
print("test MAE", result.get("metrics", {}).get("mae"))
print("test RMSE", result.get("metrics", {}).get("rmse"))
print("test R2", result.get("metrics", {}).get("r2"))
pd.read_csv(ROOT / "reports" / "model_reports" / "model_comparison.csv")
"""),
    ],
)
