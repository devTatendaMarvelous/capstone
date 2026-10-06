"""Train on rows that have a real yield value. Do not invent the target."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from evaluation.metrics import regression_metrics
from models.training import RANDOM_SEED
from utils.config import ROOT
from validation.schema import MODEL_CANDIDATE_FEATURES

WARNING = (
    "WARNING:\n"
    "The available real datasets do not contain sufficient verified Macheke farm-level "
    "maize yield observations for supervised learning.\n"
    "The dataset is therefore suitable for environmental feature analysis and data-pipeline "
    "development, but not yet sufficient for reliable farm-level yield prediction."
)


def _metrics(y_true, y_pred) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(mean_squared_error(y_true, y_pred) ** 0.5), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def annual_masks(frame: pd.DataFrame) -> dict:
    """Hold out later harvest years. One row per year cannot use a single-year validation score."""
    years = sorted(int(year) for year in frame["year"].dropna().unique())
    if len(years) < 8:
        raise ValueError("The real series needs at least eight harvest years before a temporal split.")
    test_n = max(3, len(years) // 5)
    valid_n = max(3, len(years) // 5)
    test_years = years[-test_n:]
    valid_years = years[-(test_n + valid_n):-test_n]
    train_years = years[: -(test_n + valid_n)]
    year = frame["year"].astype(int)
    return {
        "train": year.isin(train_years),
        "validation": year.isin(valid_years),
        "test": year.isin(test_years),
        "train_years": train_years,
        "validation_years": valid_years,
        "test_years": test_years,
    }


def usable_features(frame: pd.DataFrame) -> list[str]:
    chosen = []
    for column in MODEL_CANDIDATE_FEATURES:
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.notna().sum() >= 4 and values.nunique(dropna=True) >= 2:
            chosen.append(column)
    return chosen


def _candidates(seed: int) -> dict:
    return {
        "Linear Regression": Pipeline(
            [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", LinearRegression())]
        ),
        "Decision Tree Regressor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", DecisionTreeRegressor(max_depth=3, min_samples_leaf=3, random_state=seed)),
            ]
        ),
        "Random Forest Regressor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestRegressor(n_estimators=200, max_depth=4, min_samples_leaf=2, random_state=seed, n_jobs=1)),
            ]
        ),
        "Gradient Boosting Regressor": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("model", GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, max_depth=2, random_state=seed)),
            ]
        ),
    }


def train_from_real_dataset(frame: pd.DataFrame, output_dir: Path | None = None) -> dict:
    """Fit the four regressors when a real target exists. Print the farm-level warning."""
    output_dir = output_dir or (ROOT / "reports" / "model_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    farm_yields = 0
    if "yield_geographic_level" in frame.columns:
        farm_yields = int(((frame["yield_geographic_level"] == "farm") & frame["yield_t_ha"].notna()).sum())
    print(WARNING)
    labelled = frame.loc[frame["yield_t_ha"].notna()].copy()
    if len(labelled) < 8:
        status = {
            "status": "INSUFFICIENT TARGET DATA",
            "farm_level_yield_records": farm_yields,
            "yield_records": int(len(labelled)),
            "model_trained": False,
        }
        print("No supervised model was fit because fewer than eight harvest years have a real yield.")
        (output_dir / "real_model_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        return status
    features = usable_features(labelled)
    if len(features) < 2:
        status = {"status": "INSUFFICIENT TARGET DATA", "model_trained": False, "reason": "fewer than two varying predictors"}
        (output_dir / "real_model_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
        return status
    masks = annual_masks(labelled)
    comparison = []
    fitted = {}
    for name, model in _candidates(RANDOM_SEED).items():
        model.fit(labelled.loc[masks["train"], features], labelled.loc[masks["train"], "yield_t_ha"])
        predicted = model.predict(labelled.loc[masks["validation"], features])
        scores = regression_metrics(labelled.loc[masks["validation"], "yield_t_ha"], predicted)
        comparison.append({"model_name": name, "validation_mae": scores["mae"], "validation_rmse": scores["rmse"], "validation_r2": scores["r2"]})
        fitted[name] = model
    table = pd.DataFrame(comparison).sort_values(["validation_r2", "validation_rmse"], ascending=[False, True])
    chosen_name = str(table.iloc[0]["model_name"])
    chosen = fitted[chosen_name]
    test_pred = chosen.predict(labelled.loc[masks["test"], features])
    test_scores = _metrics(labelled.loc[masks["test"], "yield_t_ha"], test_pred)
    validation_pred = chosen.predict(labelled.loc[masks["validation"], features])
    importance = permutation_importance(
        chosen,
        labelled.loc[masks["validation"], features],
        labelled.loc[masks["validation"], "yield_t_ha"],
        n_repeats=10,
        random_state=RANDOM_SEED,
        scoring="r2",
    )
    importance_table = (
        pd.DataFrame({"feature": features, "importance_mean": importance.importances_mean})
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )
    importance_table.insert(0, "rank", importance_table.index + 1)
    table.to_csv(output_dir / "model_comparison.csv", index=False)
    importance_table.to_csv(output_dir / "feature_importance.csv", index=False)
    metrics = {
        "mae": test_scores["mae"],
        "rmse": test_scores["rmse"],
        "r2": test_scores["r2"],
        "test_mae": test_scores["mae"],
        "test_rmse": test_scores["rmse"],
        "test_r2": test_scores["r2"],
        "validation_mae": round(float(mean_absolute_error(labelled.loc[masks["validation"], "yield_t_ha"], validation_pred)), 4),
        "validation_rmse": round(float(mean_squared_error(labelled.loc[masks["validation"], "yield_t_ha"], validation_pred) ** 0.5), 4),
        "validation_r2": round(float(r2_score(labelled.loc[masks["validation"], "yield_t_ha"], validation_pred)), 4),
    }
    result = {
        "status": "INSUFFICIENT TARGET DATA" if farm_yields == 0 else "PASS",
        "model_trained": True,
        "chosen_model": chosen_name,
        "features": features,
        "farm_level_yield_records": farm_yields,
        "yield_records": int(len(labelled)),
        "metrics": metrics,
        "train_years": masks["train_years"],
        "validation_years": masks["validation_years"],
        "test_years": masks["test_years"],
        "disclaimer": (
            "The target is FAOSTAT national Zimbabwe maize yield in t/ha. "
            "Predictors are seasonal weather for the Macheke study-area grid. "
            "This is not a farm-level Macheke yield model. R² is not classification accuracy."
        ),
    }
    (output_dir / "real_model_status.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    import joblib

    model_path = ROOT / "models" / "trained" / "smartcrop_model.joblib"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": chosen, "features": features, "metadata": result}, model_path)
    metadata_path = ROOT / "models" / "metadata" / "model_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "model_name": "smartcrop_maize_yield",
                "version": "2.0.0-real",
                "algorithm": chosen_name,
                "features": features,
                "target": "yield_t_ha",
                "metrics": metrics,
                "dataset_version": "2.0.0-real",
                "performance_target": {"metric": "r2", "threshold": 0.8, "met": metrics["r2"] >= 0.8},
                "disclaimer": result["disclaimer"],
                "feature_importance": importance_table.to_dict(orient="records"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"Exploratory model: {chosen_name}. Test MAE {metrics['mae']}, RMSE {metrics['rmse']}, R² {metrics['r2']}. "
        "These scores describe national yield, not Macheke farm yield."
    )
    return result
