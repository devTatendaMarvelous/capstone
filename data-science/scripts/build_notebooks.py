"""Write notebooks 02–07. Run from data-science/: python scripts/build_notebooks.py"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "notebooks"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": _lines(text),
    }


def _lines(text: str) -> list[str]:
    body = text.strip("\n") + "\n"
    return [line + "\n" for line in body.split("\n")[:-1]]


def notebook(cells: list[dict]) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": cells,
    }


BOOT = """
from pathlib import Path
import sys
import pandas as pd

def find_root() -> Path:
    start = Path.cwd().resolve()
    candidates = [start, *start.parents]
    if (start / "data-science").is_dir():
        candidates.insert(0, start / "data-science")
    for candidate in candidates:
        if (candidate / "src" / "data" / "schema.py").is_file():
            return candidate
    raise FileNotFoundError("Open this notebook from the SmartCrop repository.")

ROOT = find_root()
sys.path.insert(0, str(ROOT / "src"))
pd.set_option("display.max_columns", 24)
pd.set_option("display.width", 120)
"""

NOTEBOOKS = {
    "02_data_cleaning.ipynb": [
        md("""
# SmartCrop — Notebook 02: Data Cleaning

**Study area:** Macheke, Mashonaland East, Zimbabwe  
**Crop:** maize only  
**Target:** `yield_t_ha` (tonnes per hectare)  
**Input:** `data/interim/consolidated_raw.csv`  
**Output:** `data/processed/clean_dataset.csv`

> The input file is synthetic. Cleaning does not turn it into a Macheke survey.
"""),
        md("""
## 1. Introduction

Notebook 01 consolidated two synthetic batches and left duplicates, blank cells, and a few impossible values in place. This notebook applies a written cleaning policy and saves the result. It does not impute feature gaps. Imputation is fitted later, on the training seasons only, so the clean file does not leak the test seasons.
"""),
        md("""
## 2. Objectives

1. Count rows, missing cells, and exact duplicates before cleaning.
2. Remove exact duplicate rows.
3. Blank values outside physical bounds and outside the documented plausible bounds.
4. Blank average temperature where `min <= avg <= max` fails.
5. Drop rows with no yield. Those rows cannot supervise a model.
6. Export before/after tables as CSV, Excel, and HTML.
"""),
        md("""
## 3. Dataset Description

The table is one synthetic farm in one synthetic season. `data_source_type` remains `SYNTHETIC`. Ward codes remain placeholders. Season labels remain labels, not a historical weather series. Yield is tonnes per hectare.
"""),
        md("""
## 4. Methodology

Physical bounds mark values that cannot be a measurement of that quantity, such as a negative rainfall. Plausible bounds are project checks for the injected extremes, not official agronomic limits. A value outside either bound becomes missing. The rest of the row stays.

Temperature order is checked only when minimum, average, and maximum are all present. If the order fails, the average is blanked because that is the field the generator corrupted.

Exact duplicates are identical on every column, including `record_id`. The first copy is kept.

Rows with missing `yield_t_ha` are dropped after the blanking steps, so a yield that was an injected extreme is also dropped. Feature missingness is left for the model pipeline.
"""),
        md("## 5. Implementation"),
        code(BOOT + """
from data.cleaning import clean_observations, quality_tables, write_clean_outputs
from data.schema import SYNTHETIC_DISCLAIMER, coerce_observation_frame

print(SYNTHETIC_DISCLAIMER)
raw = coerce_observation_frame(pd.read_csv(ROOT / "data" / "interim" / "consolidated_raw.csv"))
print(f"Rows before cleaning: {len(raw)}")
print(f"Exact duplicate rows before cleaning: {int(raw.duplicated().sum())}")
print(f"Missing yield rows before cleaning: {int(raw['yield_t_ha'].isna().sum())}")
"""),
        code("""
clean, report = clean_observations(raw)
tables = quality_tables(raw, clean)
paths = write_clean_outputs(clean, report, tables, ROOT)
print(f"Rows after cleaning: {report['rows_after']}")
print(f"Exact duplicates removed: {report['exact_duplicates_removed']}")
print(f"Temperature rows repaired: {report['temperature_order_repairs']}")
print(f"Rows dropped for missing yield: {report['rows_dropped_for_missing_yield']}")
print(f"Missing cells before: {report['missing_cells_before']}")
print(f"Missing cells after: {report['missing_cells_after']}")
print(f"Imputation: {report['imputation']}")
display(tables["before_after"])
display(tables["missing_by_column"])
"""),
        md("""
## 6. Results

The tables above are the cleaning log. Duplicate rows should be zero after this step. Yield should have no missing values. Some feature cells remain missing on purpose.
"""),
        md("""
## 7. Visualizations

Cleaning is summarised as a table rather than a chart. The missing-value figure for the cleaned file is drawn in Notebook 04, after this file exists.
"""),
        md("""
## 8. Interpretation

Removing exact copies stops the same farm-season from counting twice. Blanking impossible and extreme values keeps the farm row but stops a single corrupted cell from dominating a split. Dropping missing yields is required for supervised learning. Leaving other gaps unfilled avoids choosing a median from seasons that will later be used as the test set.
"""),
        md("""
## 9. Conclusion

`data/processed/clean_dataset.csv` is the modelling table. It is still synthetic maize data for the Macheke study area. The next notebook adds a short list of features that a prediction request can recompute.
"""),
    ],
    "03_feature_engineering.ipynb": [
        md("""
# SmartCrop — Notebook 03: Feature Engineering

**Target:** `yield_t_ha`  
**Principle:** add a feature only when it has an agronomic reading and the API can rebuild it from the raw inputs.
"""),
        md("""
## 1. Introduction

The clean file already stores seasonal rainfall, seasonal temperatures, soil measures, fertilizer per hectare, and a planting-day index. Copying those columns under new names would not add information. This notebook adds three contrasts that the saved model can recompute at prediction time.
"""),
        md("""
## 2. Objectives

1. Document every model input, including the columns that were deliberately not duplicated.
2. Add `temperature_range_c`, `degrees_above_33_c`, and `planting_delay_days`.
3. Export `reports/tables/feature_dictionary.xlsx`.
"""),
        md("""
## 3. Dataset Description

The input is `clean_dataset.csv`. Source columns keep their units from the schema. Engineered columns are differences or clipped delays of those source columns. `area_ha` is not a yield feature. Production, when needed, is `yield_t_ha × area_ha` and is not used to predict yield.
"""),
        md("""
## 4. Methodology

`temperature_range_c` is maximum minus minimum temperature. `degrees_above_33_c` is how far the maximum sits above 33°C, or zero when it does not. `planting_delay_days` is how many days the planting index falls after day 40, or zero when planting is earlier. Day 1 is 1 November, so day 40 is 10 December.

No critical-period rainfall feature is created. The file has one seasonal rainfall total, not dekadal rainfall. Inventing a critical-period column would pretend the file contains a split it does not have.
"""),
        md("## 5. Implementation"),
        code(BOOT + """
from data.schema import SYNTHETIC_DISCLAIMER
from features.engineering import (
    ENGINEERED_FEATURES,
    MODEL_FEATURES,
    RAW_FEATURES,
    add_engineered_features,
    feature_dictionary,
    write_feature_dictionary,
)

print(SYNTHETIC_DISCLAIMER)
clean = pd.read_csv(ROOT / "data" / "processed" / "clean_dataset.csv")
featured = add_engineered_features(clean)
dictionary_path = write_feature_dictionary(ROOT)
featured[MODEL_FEATURES + ["yield_t_ha"]].head()
"""),
        code("""
dictionary = feature_dictionary()
display(dictionary)
print("Raw inputs:", ", ".join(RAW_FEATURES))
print("Engineered:", ", ".join(ENGINEERED_FEATURES))
print(f"Feature dictionary: {dictionary_path}")
print(featured[ENGINEERED_FEATURES].describe().round(3))
"""),
        md("""
## 6. Results

The dictionary has one row per model column. Engineered columns are present on the in-memory frame. They are not stored as a second copy of rainfall or fertilizer.
"""),
        md("## 7. Visualizations\n\nFeature distributions are part of Notebook 04, where they can be read next to yield."),
        md("""
## 8. Interpretation

A wider temperature range, heat above 33°C, and planting after 10 December are readable contrasts. Whether they help the model is an evaluation question, not something this notebook assumes. Soil and fertilizer stay in their original units.
"""),
        md("""
## 9. Conclusion

The model matrix is the nine raw inputs plus three engineered columns. The prediction API will send the nine raw inputs. The saved pipeline rebuilds the three engineered columns, so a client cannot forget them or send a conflicting copy.
"""),
    ],
    "04_eda_and_descriptive_analysis.ipynb": [
        md("""
# SmartCrop — Notebook 04: Exploratory and Descriptive Analysis

**Data status:** synthetic clean maize file. Associations below were partly built by the generator. They are not findings about Macheke farms.
"""),
        md("""
## 1. Introduction

This notebook describes the clean file before any model is chosen. Charts use pairwise deletion. They do not fill missing values. Every figure is saved under `reports/figures/` with a title, axis labels, units, and a caption file.
"""),
        md("""
## 2. Objectives

Describe yield, rainfall, temperature, season, ward, fertilizer, and soil. Show a correlation matrix. Rank the five strongest linear associations with yield. Export descriptive statistics.
"""),
        md("""
## 3. Dataset Description

One row is a synthetic farm-season. Yield is tonnes per hectare. Seasons and wards are generator labels.
"""),
        md("""
## 4. Methodology

Histograms and boxplots describe each variable. Scatter plots show pairwise association. Pearson correlation ranks linear association. The top five are the largest absolute correlations with `yield_t_ha`. Correlation is not causation, and it is not the permutation importance used later.
"""),
        md("## 5. Implementation"),
        code(BOOT + """
from data.schema import SYNTHETIC_DISCLAIMER
from visualization.eda import build_eda_figures

print(SYNTHETIC_DISCLAIMER)
clean = pd.read_csv(ROOT / "data" / "processed" / "clean_dataset.csv")
numeric = ["area_ha", "rainfall_mm", "avg_temperature_c", "max_temperature_c", "min_temperature_c", "soil_ph", "soil_nitrogen", "soil_organic_carbon", "fertilizer_kg_ha", "planting_day", "yield_t_ha"]
describe = clean[numeric].describe().round(3)
describe.to_csv(ROOT / "reports" / "tables" / "descriptive_statistics.csv")
describe.to_excel(ROOT / "reports" / "tables" / "descriptive_statistics.xlsx")
print(f"Rows: {len(clean)}. Seasons: {clean['season'].nunique()}. Wards: {clean['ward'].nunique()}.")
display(describe)
"""),
        code("""
correlations = build_eda_figures(clean, ROOT / "reports" / "figures")
correlations.to_csv(ROOT / "reports" / "tables" / "feature_yield_correlations.csv", index=False)
print("Five strongest linear associations with yield")
display(correlations.head(5))
"""),
        md("""
## 6. Results

Descriptive statistics and the correlation ranking are printed above. Figure files include `yield_distribution`, `rainfall_vs_yield`, `temperature_vs_yield`, `correlation_matrix`, and `top_features`.
"""),
        md("""
## 7. Visualizations

The saved figures carry the axis labels and captions. Open `reports/figures/` beside this notebook. A positive rainfall or fertilizer correlation is expected because the generator included those terms. A weak soil correlation means that, in this synthetic file, soil varies less than rainfall and fertilizer.
"""),
        md("""
## 8. Interpretation

Use the printed top five as the descriptive answer to "which variables move together with yield in this file." Do not quote them as drivers of yield in Macheke. Season boxes compare generator season labels. Ward boxes compare placeholder codes.
"""),
        md("""
## 9. Conclusion

The clean synthetic file is described and exported. Model choice is separate and uses a temporal split so later seasons are not used to pick the algorithm.
"""),
    ],
    "05_model_training.ipynb": [
        md("""
# SmartCrop — Notebook 05: Model Training

**Target:** `yield_t_ha`  
**Candidates:** linear regression, decision tree, random forest, gradient boosting.  
XGBoost is not used. It is not required for this comparison.
"""),
        md("""
## 1. Introduction

Training estimates maize yield per hectare from weather, soil, and management inputs. The saved object is a scikit-learn pipeline: feature builder, median imputer, and the regressor. The API loads that object. It does not fit a new model when a user asks for a prediction.
"""),
        md("""
## 2. Objectives

1. Split seasons in time.
2. Fit four regressors on the earlier seasons.
3. Record training time, features, hyperparameters, validation metrics, and grouped cross-validation.
4. Save `reports/model_reports/model_comparison.csv`.
"""),
        md("""
## 3. Dataset Description

The modelling frame is the clean synthetic file. Raw inputs are rainfall, three temperatures, soil pH, soil nitrogen, soil organic carbon, fertilizer, and planting day. The pipeline adds the three engineered columns from Notebook 03.
"""),
        md("""
## 4. Methodology

Years are ordered. The earliest seasons train. The third-from-last season validates. The last two seasons are held out and are not used in this notebook.

The imputer learns medians on the training rows inside the pipeline. Grouped cross-validation splits the training window by season, so a whole season is held out of each fold. The test seasons never enter those folds.

Model choice, in the next notebooks, uses validation R². Lower validation RMSE breaks a tie.
"""),
        md("## 5. Implementation"),
        code(BOOT + """
from data.schema import SYNTHETIC_DISCLAIMER
from models.training import RANDOM_SEED, run_model_comparison

print(SYNTHETIC_DISCLAIMER)
clean = pd.read_csv(ROOT / "data" / "processed" / "clean_dataset.csv")
comparison, details = run_model_comparison(clean, RANDOM_SEED)
out = ROOT / "reports" / "model_reports"
out.mkdir(parents=True, exist_ok=True)
comparison.to_csv(out / "model_comparison.csv", index=False)
comparison.to_excel(out / "model_comparison.xlsx", index=False)
print("Train years:", details["masks"]["train_years"])
print("Validation years:", details["masks"]["validation_years"])
print("Held-out test years (not scored here):", details["masks"]["test_years"])
display(comparison.drop(columns=["hyperparameters", "features"]))
"""),
        md("""
## 6. Results

The comparison table lists each algorithm, its validation MAE, RMSE, and R², and the mean grouped cross-validation scores on the training window. R² is the coefficient of determination. It is not accuracy.
"""),
        md("## 7. Visualizations\n\nTraining comparison is a table. Residual and importance plots belong to the evaluation notebook, after a model has been selected."),
        md("""
## 8. Interpretation

A higher validation R² means the model explained more of the yield variation in the validation season. That season is still synthetic. A fast linear model can be preferred only when its validation score leads. Hyperparameters are fixed and documented in the saved table. They were not searched on the test seasons.
"""),
        md("""
## 9. Conclusion

Four models have validation scores. Notebook 06 evaluates the selection rule and the held-out seasons. Notebook 07 writes the single serialized model.
"""),
    ],
    "06_model_evaluation.ipynb": [
        md("""
# SmartCrop — Notebook 06: Model Evaluation

Metrics are MAE (t/ha), RMSE (t/ha), and R². This notebook does not report classification accuracy.
"""),
        md("""
## 1. Introduction

Evaluation asks two questions. Which candidate should be kept, using only the validation season? Once that choice is fixed, what error does it make on later seasons that it has not seen?
"""),
        md("""
## 2. Objectives

1. Select the model with the best validation R².
2. Score that model on the held-out seasons.
3. Compare the test R² with an 80% target defined as R² >= 0.80.
4. Plot actual against predicted, residuals, and the error distribution.
5. Rank inputs with permutation importance and list the top five.
"""),
        md("""
## 3. Dataset Description

The same clean synthetic file and temporal split as Notebook 05. Importance is computed on the validation season so the test season is used for the error summary rather than for explanation.
"""),
        md("""
## 4. Methodology

The academic 80% target, where a project statement asks for it, is defined here as test-set R² of at least 0.80. R² is the share of yield variance the predictions track. It is not the percentage of farms predicted exactly, and it is not classification accuracy.

Permutation importance shuffles one raw input at a time and records the drop in validation R². A large drop means the fitted model was using that input. It does not mean the input caused yield in Macheke.
"""),
        md("## 5. Implementation"),
        code(BOOT + """
from data.schema import SYNTHETIC_DISCLAIMER
from evaluation.metrics import regression_metrics
from models.training import (
    PERFORMANCE_TARGET_R2,
    RANDOM_SEED,
    evaluate_split,
    fit_final_model,
    permutation_feature_importance,
    run_model_comparison,
    select_model_name,
)
from reporting.model_report import prediction_frame, save_evaluation_figures

print(SYNTHETIC_DISCLAIMER)
clean = pd.read_csv(ROOT / "data" / "processed" / "clean_dataset.csv")
comparison, _details = run_model_comparison(clean, RANDOM_SEED)
chosen = select_model_name(comparison)
model, masks = fit_final_model(clean, chosen, RANDOM_SEED)
validation = clean.loc[clean["year"].isin(masks["validation_years"])]
test = clean.loc[clean["year"].isin(masks["test_years"])]
validation_metrics = evaluate_split(model, validation)
test_metrics = evaluate_split(model, test)
importance = permutation_feature_importance(model, validation, RANDOM_SEED)
evaluated = prediction_frame(model, test)
print(f"Selected on validation R²: {chosen}")
print(f"Validation MAE {validation_metrics['mae']:.3f}, RMSE {validation_metrics['rmse']:.3f}, R² {validation_metrics['r2']:.3f}")
print(f"Test MAE {test_metrics['mae']:.3f}, RMSE {test_metrics['rmse']:.3f}, R² {test_metrics['r2']:.3f}")
print(f"80% target means test R² >= {PERFORMANCE_TARGET_R2:.2f}. Met: {test_metrics['r2'] >= PERFORMANCE_TARGET_R2}")
display(importance)
"""),
        code("""
reports = ROOT / "reports" / "model_reports"
reports.mkdir(parents=True, exist_ok=True)
metrics = pd.DataFrame([
    {"split": "validation", "mae": validation_metrics["mae"], "rmse": validation_metrics["rmse"], "r2": validation_metrics["r2"]},
    {"split": "test", "mae": test_metrics["mae"], "rmse": test_metrics["rmse"], "r2": test_metrics["r2"]},
])
metrics.to_csv(reports / "model_metrics.csv", index=False)
comparison.to_excel(reports / "model_comparison.xlsx", index=False)
importance.to_csv(reports / "feature_importance.csv", index=False)
evaluated.to_csv(reports / "sample_predictions.csv", index=False)
save_evaluation_figures(evaluated, importance, ROOT / "reports" / "figures")
print("Wrote actual_vs_predicted, residuals, prediction_error_distribution, and feature_importance figures.")
display(metrics.round(4))
display(evaluated.head())
"""),
        md("""
## 6. Results

Read the printed test MAE, RMSE, and R². The target line states whether test R² reached 0.80. The importance table is ranked. Near-zero or negative importance means shuffling that input did not reduce validation R².
"""),
        md("""
## 7. Visualizations

`actual_vs_predicted.png` plots the test seasons against the equality line. `residuals.png` plots error against the prediction. `prediction_error_distribution.png` is the histogram of those errors, in tonnes per hectare. `feature_importance.png` shows the five highest permutation scores.
"""),
        md("""
## 8. Interpretation

Judge the model by tonnes per hectare of error, not by an accuracy percentage. If R² is below 0.80, the model does not meet the stated target on these held-out synthetic seasons. Feature importance indicates variables that contributed strongly to model predictions. It does not prove causation, and the generator itself planted relationships for rainfall, fertilizer, and planting day.
"""),
        md("""
## 9. Conclusion

The selected algorithm and its test metrics are fixed before serialization. Notebook 07 saves the pipeline and the metadata the API will load.
"""),
    ],
    "07_final_model.ipynb": [
        md("""
# SmartCrop — Notebook 07: Final Model

This notebook writes `models/trained/smartcrop_model.joblib` and `models/metadata/model_metadata.json`. The Django API loads those files and does not retrain them.
"""),
        md("""
## 1. Introduction

One pipeline is saved: the algorithm chosen on validation R², fitted to the earlier seasons, with the feature builder and the median imputer inside the file. Sample predictions from the test seasons are exported with the report.
"""),
        md("""
## 2. Objectives

1. Refit the selected model.
2. Record test metrics, row counts, features, seed, and library versions.
3. Save the joblib file, the metadata, sample predictions, and the HTML and PDF report.
4. Copy the artifact into `backend/ml_models/` for the API.
"""),
        md("""
## 3. Dataset Description

Clean synthetic maize rows. Dataset version string: `synthetic-1.0.0`. Model version string: `1.0.0`.
"""),
        md("""
## 4. Methodology

The selection rule is unchanged: highest validation R², then lower validation RMSE. Test metrics are stored after that choice. Metadata repeats the synthetic-data disclaimer so a later user of the file can see it without opening this notebook.
"""),
        md("## 5. Implementation"),
        code(BOOT + """
import json
import shutil
from data.schema import SYNTHETIC_DISCLAIMER
from models.training import (
    RANDOM_SEED,
    build_metadata,
    evaluate_split,
    fit_final_model,
    permutation_feature_importance,
    run_model_comparison,
    save_model,
    select_model_name,
)
from reporting.model_report import prediction_frame, save_evaluation_figures, write_final_report

print(SYNTHETIC_DISCLAIMER)
clean = pd.read_csv(ROOT / "data" / "processed" / "clean_dataset.csv")
comparison, _details = run_model_comparison(clean, RANDOM_SEED)
chosen = select_model_name(comparison)
model, masks = fit_final_model(clean, chosen, RANDOM_SEED)
train = clean.loc[clean["year"].isin(masks["train_years"])]
validation = clean.loc[clean["year"].isin(masks["validation_years"])]
test = clean.loc[clean["year"].isin(masks["test_years"])]
validation_metrics = evaluate_split(model, validation)
test_metrics = evaluate_split(model, test)
importance = permutation_feature_importance(model, validation, RANDOM_SEED)
samples = prediction_frame(model, test)
metadata = build_metadata(
    chosen,
    comparison,
    test_metrics,
    validation_metrics,
    train_rows=len(train),
    validation_rows=len(validation),
    test_rows=len(test),
    seed=RANDOM_SEED,
    feature_importance=importance.round(6).to_dict(orient="records"),
)
paths = save_model(model, metadata, ROOT)
save_evaluation_figures(samples, importance, ROOT / "reports" / "figures")
reports = write_final_report(ROOT, metadata, comparison, importance, samples)
backend = ROOT.parent / "backend" / "ml_models"
backend.mkdir(parents=True, exist_ok=True)
shutil.copy2(paths["model"], backend / "smartcrop_model.joblib")
shutil.copy2(paths["metadata"], backend / "model_metadata.json")
print(json.dumps({
    "algorithm": metadata["algorithm"],
    "version": metadata["version"],
    "test_r2": metadata["metrics"]["test_r2"],
    "target_met": metadata["performance_target"]["met"],
    "model": str(paths["model"]),
    "html": str(reports["html"]),
    "pdf": str(reports["pdf"]),
}, indent=2))
display(samples.head(8))
"""),
        md("""
## 6. Results

The printed JSON is the serialization receipt: algorithm, version, test R², whether the 0.80 R² target was met, and the file paths. Sample test predictions are displayed. They are model output, not observations.
"""),
        md("## 7. Visualizations\n\nThe report embeds the actual-versus-predicted figure. The HTML and PDF reports are written to `reports/final_model_report.html` and `reports/final_model_report.pdf`."),
        md("""
## 8. Interpretation

Use the saved metrics as the performance of this synthetic experiment. A prediction from the API is an estimate from this pipeline. It is not a guaranteed yield, and it is not a measurement from a Macheke field.
"""),
        md("""
## 9. Conclusion

The research path from the consolidated file to a versioned model file is complete for maize in the Macheke study area. Later seasons were held out. The API should load `smartcrop_model.joblib` and refuse to train during a request.
"""),
    ],
}


def main() -> None:
    for name, cells in NOTEBOOKS.items():
        path = OUT / name
        path.write_text(json.dumps(notebook(cells), indent=1), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
