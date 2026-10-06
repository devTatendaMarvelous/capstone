# SmartCrop

SmartCrop is a university prototype for **maize yield prediction** in **Macheke, Mashonaland East, Zimbabwe**. The model target is `yield_t_ha`, maize grain yield in tonnes per hectare.

If cultivated area is supplied, production is derived after the prediction:

```text
predicted_production_tonnes = predicted_yield_t_ha × area_ha
```

`area_ha` is not a model feature. The scope is maize in this study area. The prototype does not predict other crops, pests, prices, or irrigation schedules. Satellite imagery and IoT sensors are not part of this version.

**The training file is synthetic.** Rows in `data-science/data/synthetic/` were generated for software and model-development exercises. They are not a survey of Macheke farms and must not be cited as ZIMSTAT, Agritex, NASA POWER, CHIRPS, or SoilGrids measurements. `data_source_type` is `REAL`, `SYNTHETIC`, or `EXTERNAL`. Every generated observation is `SYNTHETIC`.

## Model result

Saved model: Random Forest regressor, version `1.0.0`, seed 42, dataset `synthetic-1.0.0`.

Held-out test seasons (last two season labels, 235 rows):

| Metric | Value |
| --- | --- |
| MAE | 0.2644 t/ha |
| RMSE | 0.3422 t/ha |
| R² | 0.4675 |

The academic target used here is **test R² ≥ 0.80**. That target is **not met**. R² is the coefficient of determination for a continuous yield. It is not classification accuracy, so 0.47 is not “47% accuracy.”

Model choice used the validation season only (the third-from-last season). Every candidate had a negative validation R² on that season. Random Forest was the least poor (−0.31), ahead of gradient boosting, a depth-limited decision tree, and linear regression. The test set was not used to pick the algorithm. Grouped cross-validation inside the training window was higher (Random Forest CV R² about 0.48), which shows the single validation season is a hard shift, not a reason to treat the test score as a selection score.

Permutation importance on the validation season, which is association under this generator and not a causal ranking: fertilizer rate, rainfall, then planting day. Soil nitrogen and average temperature were near zero.

Clean table: 938 rows after dropping exact duplicates, blanking implausible values, and dropping rows with missing yield. Median imputation stays inside the scikit-learn pipeline and is fit on the training window only.

## Architecture

```text
raw data → clean data → features → analysis → model → prediction → reporting
```

```text
Data science (Python notebooks and src/)
        │
        ▼
models/trained/smartcrop_model.joblib + metadata
        │
        ▼
Django REST API (loads the file; a request never retrains)
        │
        ▼
React app (dashboard, prediction, history, analytics, reports)
```

One application is enough. There is no microservice split.

## Repository

```text
smartcrop/
├── README.md
├── .env.example
├── docker-compose.yml
├── docker/
├── data-science/     schema, generator, notebooks 01–07, saved model
├── backend/          Django API, admin, tests
└── frontend/         React, Vite, Tailwind
```

## Run the data-science pipeline

Python 3.11 or newer.

```bash
cd data-science
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_synthetic_dataset.py
python scripts/run_research_pipeline.py
pytest
```

Notebooks `01` through `07` cover acquisition, cleaning, features, EDA, training, evaluation, and the saved model. HTML copies are written by:

```bash
python scripts/export_notebooks.py
```

The model report PDF is ReportLab (`reports/final_model_report.pdf`). Notebook PDF export needs LaTeX and is not required.

## Run the API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

SQLite is the local default. Set `DATABASE_URL` to a `postgres://` URL to use PostgreSQL. Copy `.env.example` to `.env` and do not commit it.

`seed_demo` creates `admin`, `researcher`, `analyst`, and `farmer`. The password is `SMARTCROP_DEMO_PASSWORD`, or `password` when that variable is unset. Change it before any shared deployment. Registration through the API creates a farmer account only.

- API docs: http://127.0.0.1:8000/api/docs/
- ReDoc: http://127.0.0.1:8000/api/redoc/
- Schema: http://127.0.0.1:8000/api/schema/
- Admin: http://127.0.0.1:8000/admin/

```bash
pytest
```

A prediction posts rainfall, temperatures, soil pH, soil nitrogen, soil organic carbon (percent), fertilizer kg/ha, planting day, and area in hectares. `soil_organic_carbon` is required. The response includes `predicted_yield_t_ha`, `predicted_production_tonnes`, `model_version`, a short interpretation, and a synthetic-data disclaimer.

Reports: `GET /api/v1/reports/{predictions,model-performance,dataset,analytics}/?format=pdf|xlsx|csv`.

## Run the frontend

Node 22. The dev server proxies `/api` to `http://127.0.0.1:8000`.

```bash
cd frontend
npm install
npm test
npm run dev
```

Open http://127.0.0.1:5173 and sign in with a seeded account. Pages: dashboard, prediction, history, analytics, reports, datasets, models, profile, and an admin view for the admin role.

## Docker Compose

From the repository root, with Docker available:

```bash
docker compose up --build
```

PostgreSQL is on port 5432, the API on port 8000, and the built frontend on port 8080. Compose uses the local default password `smartcrop` for Postgres and `password` for the demo users. Those are development defaults, not production secrets. The saved model and the clean CSV are mounted into the API container; the container does not retrain.

## Roles

| Role | What they can do |
| --- | --- |
| farmer | Predict, see their own history, download reports, read model metrics |
| analyst | Same, plus system-wide prediction history and analytics |
| researcher | Analyst access, plus dataset upload |
| admin | Researcher access, plus user list, model activation, and Django admin |

## Assumptions and limitations

- Ward codes `SYN-W01`–`SYN-W06` are placeholders. Season labels are generator labels, not historical weather years.
- Planting day 1 is 1 November. Fertilizer is product kilograms per hectare. Soil organic carbon is percent; a SoilGrids value in g/kg would be divided by 10 before use.
- Cleaning does not impute in the saved clean file. The training pipeline imputes medians from the training rows only.
- Permutation importance is not a fertilizer recommendation and not evidence from Macheke fields.
- The 0.80 R² target is unmet on synthetic data with this temporal split. Do not describe the model as 80% accurate.
- Predictions are estimates. They are not a guaranteed harvest.
