"""Run cleaning, features, training, evaluation, and the final report.

Notebooks call the same functions. This script is the non-interactive path.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data.cleaning import clean_observations, quality_tables, write_clean_outputs  # noqa: E402
from data.schema import SYNTHETIC_DISCLAIMER, coerce_observation_frame  # noqa: E402
from evaluation.metrics import regression_metrics  # noqa: E402
from features.engineering import write_feature_dictionary  # noqa: E402
from models.training import (  # noqa: E402
    RANDOM_SEED,
    build_metadata,
    evaluate_split,
    fit_final_model,
    permutation_feature_importance,
    run_model_comparison,
    save_model,
    select_model_name,
)
from reporting.model_report import prediction_frame, save_evaluation_figures, write_final_report  # noqa: E402
from visualization.eda import build_eda_figures  # noqa: E402


def ds_root() -> Path:
    return ROOT


def run(root: Path | None = None) -> dict:
    raise RuntimeError(
        "The synthetic research pipeline is disabled. "
        "Use scripts/acquire_all.py, scripts/build_dataset.py, and scripts/validate_dataset.py."
    )
    root = ds_root() if root is None else Path(root)
    raw_path = root / "data" / "interim" / "consolidated_raw.csv"
    if not raw_path.is_file():
        raise FileNotFoundError(f"Missing {raw_path}. Run Notebook 01 or the generator first.")

    raw = coerce_observation_frame(pd.read_csv(raw_path))
    clean, cleaning_log = clean_observations(raw)
    tables = quality_tables(raw, clean)
    write_clean_outputs(clean, cleaning_log, tables, root)
    write_feature_dictionary(root)

    figures = root / "reports" / "figures"
    correlations = build_eda_figures(clean, figures)
    correlations.to_csv(root / "reports" / "tables" / "feature_yield_correlations.csv", index=False)

    comparison, details = run_model_comparison(clean, RANDOM_SEED)
    reports_dir = root / "reports" / "model_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = reports_dir / "model_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    comparison.to_excel(reports_dir / "model_comparison.xlsx", index=False)

    chosen = select_model_name(comparison)
    model, masks = fit_final_model(clean, chosen, RANDOM_SEED)
    validation = clean.loc[clean["year"].astype(int).isin(masks["validation_years"])].copy()
    test = clean.loc[clean["year"].astype(int).isin(masks["test_years"])].copy()
    train = clean.loc[clean["year"].astype(int).isin(masks["train_years"])].copy()
    validation_metrics = evaluate_split(model, validation)
    test_metrics = evaluate_split(model, test)
    importance = permutation_feature_importance(model, validation, RANDOM_SEED)
    importance.to_csv(reports_dir / "feature_importance.csv", index=False)
    samples = prediction_frame(model, test)
    samples.to_csv(reports_dir / "sample_predictions.csv", index=False)
    metrics_table = pd.DataFrame(
        [
            {"split": "validation", **{key: value for key, value in validation_metrics.items() if key != "rows"}},
            {"split": "test", **{key: value for key, value in test_metrics.items() if key != "rows"}},
        ]
    )
    metrics_table.to_csv(reports_dir / "model_metrics.csv", index=False)
    save_evaluation_figures(samples, importance, figures)

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
    paths = save_model(model, metadata, root)
    report_paths = write_final_report(root, metadata, comparison, importance, samples)

    backend_models = root.parent / "backend" / "ml_models"
    backend_models.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths["model"], backend_models / "smartcrop_model.joblib")
    shutil.copy2(paths["metadata"], backend_models / "model_metadata.json")

    summary = {
        "disclaimer": SYNTHETIC_DISCLAIMER,
        "rows_clean": int(len(clean)),
        "chosen_model": chosen,
        "test_metrics": {key: round(float(test_metrics[key]), 4) for key in ("mae", "rmse", "r2")},
        "top_features": importance.head(5)[["rank", "feature", "importance_mean"]].to_dict(orient="records"),
        "model_path": str(paths["model"]),
        "report_html": str(report_paths["html"]),
        "report_pdf": str(report_paths["pdf"]),
    }
    (reports_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
