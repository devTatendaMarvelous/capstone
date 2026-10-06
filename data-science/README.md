# SmartCrop data science

Maize yield pipeline for Macheke, Mashonaland East. It runs without the Django API.

Real acquisition is documented in `README_DATA_ACQUISITION.md`. The synthetic generator is archived under `archive/synthetic/` and is not used to build `data/processed/modelling_dataset.csv`.

**The file `data/synthetic/macheke_maize_synthetic.csv` is an archived synthetic exercise.** It is not a Macheke farm survey. See `data/synthetic/README.md`.

## Layout

```text
data-science/
├── generate_synthetic_dataset.py
├── scripts/run_research_pipeline.py
├── scripts/export_notebooks.py
├── notebooks/01_… through 07_…
├── src/data/                 schema, quality, generator, cleaning
├── src/features/             engineered features
├── src/visualization/        figures and EDA
├── src/evaluation/           MAE, RMSE, R²
├── src/models/               comparison, selection, joblib save
├── src/reporting/            HTML and PDF model report
├── data/raw/                 CSV and Excel batches
├── data/external/            source catalogue (no measurements)
├── data/synthetic/           labelled synthetic master file
├── data/interim/             consolidated_raw.csv
├── data/processed/           clean_dataset.csv
├── models/trained/           smartcrop_model.joblib
├── models/metadata/          model_metadata.json
└── reports/                  figures, tables, model report
```

## Setup

```bash
cd data-science
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## Generate and run

```bash
python generate_synthetic_dataset.py
python scripts/run_research_pipeline.py
python scripts/export_notebooks.py
```

`--number-of-records` defaults to 960, `--number-of-seasons` to 8, `--random-seed` to 42, `--missing-rate` to 0.03, `--outlier-rate` to 0.02, and `--duplicate-rate` to 0.015. The same seed writes the same measurements, blanks, outliers, and duplicate copies.

The generator labels every observation `SYNTHETIC`, keeps a mild documented link between rainfall, temperature, soil, fertilizer, planting day, and yield, and does not use area in the yield formula.

Notebooks:

| Notebook | What it does |
| --- | --- |
| 01 | Load CSV and Excel batches and write the consolidated raw table |
| 02 | Drop exact duplicates, blank implausible values, drop missing yield |
| 03 | Add temperature range, degrees above 33 °C, and planting delay |
| 04 | Descriptive statistics and figures |
| 05 | Compare linear regression, decision tree, random forest, and gradient boosting |
| 06 | Score the chosen model on the held-out seasons |
| 07 | Fit the final pipeline and save joblib plus metadata |

The temporal split keeps the earliest seasons for training, the third-from-last season for validation, and the last two seasons for test. The algorithm is chosen by validation R², then lower RMSE. The test set is not used for that choice. Median imputation is inside the scikit-learn pipeline.

Saved result for seed 42: Random Forest, test MAE 0.2644, RMSE 0.3422, R² 0.4675. The test R² target of 0.80 is not met. R² is not classification accuracy. The copy used by the API is `backend/ml_models/`.

## Schema

The column contract is `src/data/schema.py` (`SCHEMA_VERSION` 1.0.0). The target is `yield_t_ha`. `data_source_type` is `REAL`, `SYNTHETIC`, or `EXTERNAL`. Do not append a real extract to the synthetic file without that column filled in.
