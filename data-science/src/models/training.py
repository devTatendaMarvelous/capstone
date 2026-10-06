"""Train, compare, and serialize the maize yield models.

The split is temporal. Earlier seasons train the model. One later season
validates model choice. The final seasons are touched once, for the chosen
model's test metrics. Random row shuffling is not used for the main split
because a future season would leak into training.
"""

from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

from data.schema import SCHEMA_VERSION, SYNTHETIC_DISCLAIMER, TARGET_COLUMN
from evaluation.metrics import regression_metrics
from features.engineering import MODEL_FEATURES, RAW_FEATURES, add_engineered_features

PERFORMANCE_TARGET_R2 = 0.80
RANDOM_SEED = 42


class FeatureBuilder(BaseEstimator, TransformerMixin):
    """Build engineered columns from the raw prediction inputs."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        frame = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=RAW_FEATURES)
        missing = [column for column in RAW_FEATURES if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing model inputs: {missing}")
        built = add_engineered_features(frame)
        return built.loc[:, MODEL_FEATURES].to_numpy(dtype=float)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(MODEL_FEATURES, dtype=object)


def temporal_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Last two seasons test, the season before that validates, earlier seasons train."""
    years = sorted(int(year) for year in df["year"].dropna().unique())
    if len(years) < 4:
        raise ValueError("Temporal split needs at least four seasons.")
    test_years = set(years[-2:])
    valid_years = {years[-3]}
    train_years = set(years[:-3])
    year = df["year"].astype(int)
    return {
        "train": year.isin(train_years),
        "validation": year.isin(valid_years),
        "test": year.isin(test_years),
        "train_years": sorted(train_years),
        "validation_years": sorted(valid_years),
        "test_years": sorted(test_years),
    }


def candidate_models(seed: int = RANDOM_SEED) -> dict[str, BaseEstimator]:
    """Four regressors. XGBoost is intentionally not required."""
    return {
        "Linear Regression": Pipeline(
            [
                ("features", FeatureBuilder()),
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ]
        ),
        "Decision Tree Regressor": Pipeline(
            [
                ("features", FeatureBuilder()),
                ("imputer", SimpleImputer(strategy="median")),
                ("model", DecisionTreeRegressor(max_depth=4, min_samples_leaf=10, random_state=seed)),
            ]
        ),
        "Random Forest Regressor": Pipeline(
            [
                ("features", FeatureBuilder()),
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestRegressor(
                    n_estimators=200,
                    max_depth=8,
                    min_samples_leaf=5,
                    random_state=seed,
                    n_jobs=1,
                )),
            ]
        ),
        "Gradient Boosting Regressor": Pipeline(
            [
                ("features", FeatureBuilder()),
                ("imputer", SimpleImputer(strategy="median")),
                ("model", GradientBoostingRegressor(
                    n_estimators=150,
                    learning_rate=0.05,
                    max_depth=3,
                    random_state=seed,
                )),
            ]
        ),
    }


def _xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return df.loc[:, RAW_FEATURES], df[TARGET_COLUMN].astype(float)


def cross_validate_train(model, train: pd.DataFrame, seed: int) -> dict[str, float]:
    """Group seasons inside the training window. The test seasons stay out."""
    groups = train["season"].astype(str)
    n_groups = groups.nunique()
    splits = min(4, n_groups)
    if splits < 2:
        return {"cv_mae": float("nan"), "cv_rmse": float("nan"), "cv_r2": float("nan")}
    folder = GroupKFold(n_splits=splits)
    x_frame, y = _xy(train)
    scores = []
    for train_index, valid_index in folder.split(x_frame, y, groups):
        candidate = clone(model)
        candidate.fit(x_frame.iloc[train_index], y.iloc[train_index])
        predicted = candidate.predict(x_frame.iloc[valid_index])
        scores.append(regression_metrics(y.iloc[valid_index], predicted))
    frame = pd.DataFrame(scores)
    return {
        "cv_mae": float(frame["mae"].mean()),
        "cv_rmse": float(frame["rmse"].mean()),
        "cv_r2": float(frame["r2"].mean()),
    }


def run_model_comparison(df: pd.DataFrame, seed: int = RANDOM_SEED) -> tuple[pd.DataFrame, dict]:
    """Fit every candidate on the training seasons and score the validation season."""
    masks = temporal_masks(df)
    train = df.loc[masks["train"]].copy()
    valid = df.loc[masks["validation"]].copy()
    x_train, y_train = _xy(train)
    x_valid, y_valid = _xy(valid)
    rows = []
    fitted = {}
    for name, model in candidate_models(seed).items():
        started = time.perf_counter()
        model.fit(x_train, y_train)
        elapsed = time.perf_counter() - started
        predicted = model.predict(x_valid)
        metrics = regression_metrics(y_valid, predicted)
        cv_scores = cross_validate_train(model, train, seed)
        hyperparameters = model.named_steps["model"].get_params()
        rows.append(
            {
                "model_name": name,
                "training_seconds": round(elapsed, 4),
                "features": ", ".join(MODEL_FEATURES),
                "hyperparameters": json.dumps({key: _jsonable(value) for key, value in hyperparameters.items() if key != "n_jobs" or True}),
                "validation_mae": round(metrics["mae"], 4),
                "validation_rmse": round(metrics["rmse"], 4),
                "validation_r2": round(metrics["r2"], 4),
                **{key: round(value, 4) if pd.notna(value) else None for key, value in cv_scores.items()},
                "train_rows": int(len(train)),
                "validation_rows": int(len(valid)),
            }
        )
        fitted[name] = model
    comparison = pd.DataFrame(rows).sort_values(
        ["validation_r2", "validation_rmse"], ascending=[False, True]
    ).reset_index(drop=True)
    details = {
        "masks": {key: value for key, value in masks.items() if key.endswith("years")},
        "fitted": fitted,
        "train": train,
        "validation": valid,
        "test": df.loc[masks["test"]].copy(),
    }
    return comparison, details


def select_model_name(comparison: pd.DataFrame) -> str:
    """Choose the validation R² leader. RMSE breaks a tie. The test set is not used."""
    ordered = comparison.sort_values(["validation_r2", "validation_rmse"], ascending=[False, True])
    return str(ordered.iloc[0]["model_name"])


def permutation_feature_importance(model, validation: pd.DataFrame, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Importance on the validation season.

    Permutation importance shows which inputs the fitted model relied on.
    It does not show that a variable caused yield.
    """
    x_valid, y_valid = _xy(validation)
    result = permutation_importance(
        model,
        x_valid,
        y_valid,
        n_repeats=10,
        random_state=seed,
        scoring="r2",
    )
    table = pd.DataFrame(
        {
            "feature": RAW_FEATURES,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)
    table.insert(0, "rank", range(1, len(table) + 1))
    return table.reset_index(drop=True)


def fit_final_model(df: pd.DataFrame, model_name: str, seed: int = RANDOM_SEED):
    """Refit the chosen algorithm on training seasons only."""
    masks = temporal_masks(df)
    train = df.loc[masks["train"]].copy()
    model = candidate_models(seed)[model_name]
    x_train, y_train = _xy(train)
    model.fit(x_train, y_train)
    return model, masks


def evaluate_split(model, frame: pd.DataFrame) -> dict[str, float]:
    predicted = model.predict(frame.loc[:, RAW_FEATURES])
    metrics = regression_metrics(frame[TARGET_COLUMN], predicted)
    return {**metrics, "rows": int(len(frame))}


def build_metadata(
    model_name: str,
    comparison: pd.DataFrame,
    test_metrics: dict,
    validation_metrics: dict,
    train_rows: int,
    validation_rows: int,
    test_rows: int,
    seed: int,
    dataset_version: str = "synthetic-1.0.0",
    feature_importance: list[dict] | None = None,
) -> dict:
    import numpy
    import sklearn

    chosen = comparison.loc[comparison["model_name"] == model_name].iloc[0]
    return {
        "model_name": "smartcrop_maize_yield",
        "version": "1.0.0",
        "algorithm": model_name,
        "training_date": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "features": MODEL_FEATURES,
        "raw_features": RAW_FEATURES,
        "target": TARGET_COLUMN,
        "metrics": {
            "validation_mae": float(chosen["validation_mae"]),
            "validation_rmse": float(chosen["validation_rmse"]),
            "validation_r2": float(chosen["validation_r2"]),
            "test_mae": round(test_metrics["mae"], 4),
            "test_rmse": round(test_metrics["rmse"], 4),
            "test_r2": round(test_metrics["r2"], 4),
            "mae": round(test_metrics["mae"], 4),
            "rmse": round(test_metrics["rmse"], 4),
            "r2": round(test_metrics["r2"], 4),
        },
        "performance_target": {
            "metric": "r2",
            "threshold": PERFORMANCE_TARGET_R2,
            "split": "held-out later seasons",
            "definition": (
                "The academic 80% target is defined here as test-set R² of at least 0.80. "
                "R² is the coefficient of determination, not classification accuracy."
            ),
            "met": bool(test_metrics["r2"] >= PERFORMANCE_TARGET_R2),
        },
        "training_records": train_rows,
        "validation_records": validation_rows,
        "test_records": test_rows,
        "validation_metrics_repeat": {key: round(float(value), 4) for key, value in validation_metrics.items() if key != "rows"},
        "dataset_version": dataset_version,
        "schema_version": SCHEMA_VERSION,
        "random_seed": seed,
        "framework_versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": numpy.__version__,
        },
        "disclaimer": SYNTHETIC_DISCLAIMER,
        "feature_importance": feature_importance or [],
        "feature_importance_note": (
            "Permutation importance on the validation season. "
            "It indicates inputs that contributed to predictions. It does not prove causation."
        ),
        "selection_rule": "Highest validation R². Lower validation RMSE breaks a tie. The test seasons are not used to choose the model.",
        "crop": "maize",
        "location": "Macheke",
        "province": "Mashonaland East",
        "country": "Zimbabwe",
    }


def save_model(model, metadata: dict, root: Path) -> dict[str, Path]:
    trained = root / "models" / "trained"
    meta_dir = root / "models" / "metadata"
    trained.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)
    model_path = trained / "smartcrop_model.joblib"
    metadata_path = meta_dir / "model_metadata.json"
    joblib.dump(model, model_path)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"model": model_path, "metadata": metadata_path}


def _jsonable(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
