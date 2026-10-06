"""Evaluation plots and the final research report."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from data.schema import SYNTHETIC_DISCLAIMER, TARGET_COLUMN
from features.engineering import RAW_FEATURES
from visualization.figures import apply_style, save_figure


def prediction_frame(model, frame: pd.DataFrame) -> pd.DataFrame:
    predicted = model.predict(frame.loc[:, RAW_FEATURES])
    out = frame[["record_id", "season", "year", "ward", TARGET_COLUMN]].copy()
    out["predicted_yield_t_ha"] = np.round(predicted, 3)
    out["residual_t_ha"] = (out[TARGET_COLUMN] - out["predicted_yield_t_ha"]).round(3)
    return out


def save_evaluation_figures(evaluated: pd.DataFrame, importance: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    apply_style()
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(evaluated[TARGET_COLUMN], evaluated["predicted_yield_t_ha"], alpha=0.5, s=18, c="#2F6B4F")
    low = float(min(evaluated[TARGET_COLUMN].min(), evaluated["predicted_yield_t_ha"].min()))
    high = float(max(evaluated[TARGET_COLUMN].max(), evaluated["predicted_yield_t_ha"].max()))
    ax.plot([low, high], [low, high], color="#8C4A32", linewidth=1)
    ax.set_title("Actual and predicted maize yield on the test seasons")
    ax.set_xlabel("Actual yield (t/ha)")
    ax.set_ylabel("Predicted yield (t/ha)")
    fig.tight_layout()
    save_figure(
        fig,
        figures_dir / "actual_vs_predicted",
        "Test-season predictions against the synthetic yield. The line is equality, not a causal claim.",
    )

    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(evaluated["predicted_yield_t_ha"], evaluated["residual_t_ha"], alpha=0.5, s=18, c="#4C7C8A")
    ax.axhline(0, color="#8C4A32", linewidth=1)
    ax.set_title("Residuals on the test seasons")
    ax.set_xlabel("Predicted yield (t/ha)")
    ax.set_ylabel("Residual (actual minus predicted, t/ha)")
    fig.tight_layout()
    save_figure(fig, figures_dir / "residuals", "Test-season residuals. A pattern here would mean the model missed a systematic effect.")

    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(evaluated["residual_t_ha"], bins=20, color="#2F6B4F", edgecolor="white")
    ax.set_title("Distribution of prediction error on the test seasons")
    ax.set_xlabel("Residual (t/ha)")
    ax.set_ylabel("Test observations")
    fig.tight_layout()
    save_figure(fig, figures_dir / "prediction_error_distribution", "Histogram of test residuals in tonnes per hectare.")

    apply_style()
    top = importance.head(5)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(top["feature"][::-1], top["importance_mean"][::-1], color="#2F6B4F")
    ax.set_title("Top five inputs by permutation importance")
    ax.set_xlabel("Mean decrease in validation R² when shuffled")
    ax.set_ylabel("Input")
    fig.tight_layout()
    save_figure(
        fig,
        figures_dir / "feature_importance",
        "Permutation importance on the validation season. It indicates inputs the model used. It does not prove causation.",
    )


def write_final_report(
    root: Path,
    metadata: dict,
    comparison: pd.DataFrame,
    importance: pd.DataFrame,
    sample_predictions: pd.DataFrame,
) -> dict[str, Path]:
    """Write the HTML and PDF research summary from the saved metrics."""
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    html_path = reports / "final_model_report.html"
    pdf_path = reports / "final_model_report.pdf"
    html_path.write_text(_html(metadata, comparison, importance, sample_predictions), encoding="utf-8")
    _pdf(pdf_path, root, metadata, comparison, importance)
    return {"html": html_path, "pdf": pdf_path}


def _html(metadata, comparison, importance, samples) -> str:
    metrics = metadata["metrics"]
    target = metadata["performance_target"]
    rows = comparison.to_html(index=False, float_format=lambda value: f"{value:.4f}" if isinstance(value, float) else str(value))
    importance_html = importance.head(5).to_html(index=False, float_format=lambda value: f"{value:.4f}" if isinstance(value, float) else str(value))
    sample_html = samples.head(8).to_html(index=False)
    met = "met" if target["met"] else "not met"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>SmartCrop final model report</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 920px; color: #1c2416; line-height: 1.45; }}
    h1 {{ font-size: 1.6rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
    th, td {{ border: 1px solid #cfc6b8; padding: 0.35rem 0.45rem; text-align: left; }}
    th {{ background: #e7efe4; }}
    .note {{ background: #f6f1e7; padding: 0.8rem 1rem; }}
  </style>
</head>
<body>
  <h1>SmartCrop final model report</h1>
  <p>Maize yield in tonnes per hectare. Study area label: Macheke, Mashonaland East, Zimbabwe.</p>
  <p class="note">{metadata["disclaimer"]}</p>
  <h2>Selected model</h2>
  <p>Algorithm: {metadata["algorithm"]}. Version: {metadata["version"]}.
  Trained: {metadata["training_date"]}. Dataset version: {metadata["dataset_version"]}.</p>
  <p>Selection rule: {metadata["selection_rule"]}</p>
  <h2>Test metrics</h2>
  <p>MAE {metrics["test_mae"]:.3f} t/ha. RMSE {metrics["test_rmse"]:.3f} t/ha. R² {metrics["test_r2"]:.3f}.</p>
  <p>The 80% performance target is defined as test R² of at least {target["threshold"]:.2f}.
  That target is {met}. This R² is the coefficient of determination, not classification accuracy.</p>
  <p>Training rows: {metadata["training_records"]}. Validation rows: {metadata["validation_records"]}.
  Test rows: {metadata["test_records"]}. Seed: {metadata["random_seed"]}.</p>
  <h2>Model comparison</h2>
  {rows}
  <h2>Top five permutation importances</h2>
  <p>Feature importance indicates variables that contributed strongly to model predictions. It does not prove causation.</p>
  {importance_html}
  <h2>Sample test predictions</h2>
  {sample_html}
</body>
</html>
"""


def _pdf(path: Path, root: Path, metadata: dict, comparison: pd.DataFrame, importance: pd.DataFrame) -> None:
    styles = getSampleStyleSheet()
    story = [
        Paragraph("SmartCrop — maize yield model report", styles["Title"]),
        Paragraph("Macheke, Mashonaland East, Zimbabwe. Crop: maize. Target: yield_t_ha.", styles["Normal"]),
        Spacer(1, 0.3 * cm),
        Paragraph(SYNTHETIC_DISCLAIMER, styles["Italic"]),
        Spacer(1, 0.4 * cm),
        Paragraph(
            f"Algorithm: {metadata['algorithm']} {metadata['version']}. "
            f"Test MAE {metadata['metrics']['test_mae']:.3f} t/ha, "
            f"RMSE {metadata['metrics']['test_rmse']:.3f} t/ha, "
            f"R² {metadata['metrics']['test_r2']:.3f}.",
            styles["Normal"],
        ),
        Paragraph(metadata["performance_target"]["definition"], styles["Normal"]),
        Spacer(1, 0.4 * cm),
    ]
    figure = root / "reports" / "figures" / "actual_vs_predicted.png"
    if figure.is_file():
        story.append(Image(str(figure), width=12 * cm, height=10 * cm))
        story.append(Spacer(1, 0.3 * cm))
    header = ["Model", "Validation R²", "Validation RMSE", "Validation MAE"]
    data = [header]
    for row in comparison.itertuples(index=False):
        data.append([
            row.model_name,
            f"{row.validation_r2:.3f}",
            f"{row.validation_rmse:.3f}",
            f"{row.validation_mae:.3f}",
        ])
    table = Table(data, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EFE4")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8A8175")),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "Top inputs by permutation importance. This is contribution to predictions, not causation.",
        styles["Normal"],
    ))
    for row in importance.head(5).itertuples(index=False):
        story.append(Paragraph(f"{row.rank}. {row.feature}: {row.importance_mean:.3f}", styles["Normal"]))
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="SmartCrop final model report")
    doc.build(story)
