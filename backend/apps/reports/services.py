"""Build short PDF, Excel, and CSV reports from stored SmartCrop data."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.analytics.services import overview_for
from apps.datasets.models import DatasetVersion
from apps.datasets.quality import quality_report
from apps.models_registry.models import ModelVersion
from apps.predictions.models import Prediction

DISCLAIMER = (
    "SmartCrop estimates maize yield in tonnes per hectare for the Macheke study area. "
    "A prediction is a model estimate, not a guaranteed harvest. "
    "Model 1.0.0 was trained on synthetic development data."
)


def render_report(report_type: str, export_format: str, user) -> tuple[bytes, str, str]:
    title, headers, rows, notes = _content(report_type, user)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if export_format == "csv":
        body = _csv(headers, rows)
        media = "text/csv"
    elif export_format == "xlsx":
        body = _xlsx(title, stamp, headers, rows, notes)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif export_format == "pdf":
        chart = _chart(report_type, user)
        body = _pdf(title, stamp, headers, rows, notes, chart)
        media = "application/pdf"
    else:
        raise ValueError("format must be pdf, xlsx, or csv.")
    filename = f"smartcrop-{report_type}.{export_format if export_format != 'xlsx' else 'xlsx'}"
    return body, media, filename


def _content(report_type: str, user):
    if report_type == "predictions":
        return _predictions(user)
    if report_type == "model-performance":
        return _model()
    if report_type == "dataset":
        return _dataset()
    if report_type == "analytics":
        return _analytics(user)
    raise ValueError("Unknown report type.")


def _predictions(user):
    queryset = Prediction.objects.select_related("user")
    if user.role == "farmer" and not user.is_superuser:
        queryset = queryset.filter(user=user)
    rows = [
        [
            item.created_at.strftime("%Y-%m-%d %H:%M"),
            item.user.username,
            item.model_version,
            item.farm_area,
            item.predicted_yield,
            item.predicted_production,
        ]
        for item in queryset[:200]
    ]
    average = ""
    if rows:
        average = round(sum(row[4] for row in rows) / len(rows), 3)
    notes = [
        f"Rows in this report: {len(rows)} (most recent 200).",
        f"Average predicted yield in this extract: {average} t/ha." if average != "" else "No predictions stored.",
        "Production is predicted yield multiplied by the area sent with the request.",
    ]
    headers = ["Created", "User", "Model", "Area ha", "Yield t/ha", "Production t"]
    return "SmartCrop prediction report", headers, rows, notes


def _model():
    active = ModelVersion.objects.filter(is_active=True).first()
    if active is None:
        return "SmartCrop model performance", ["Item", "Value"], [["Active model", "None"]], ["No model is marked active."]
    metrics = active.metrics or {}
    rows = [
        ["Name", active.name],
        ["Version", active.version],
        ["Algorithm", active.algorithm],
        ["Target", active.target_variable],
        ["Dataset version", active.dataset_version],
        ["Test MAE (t/ha)", metrics.get("mae")],
        ["Test RMSE (t/ha)", metrics.get("rmse")],
        ["Test R²", metrics.get("r2")],
    ]
    importance = []
    try:
        from apps.predictions.ml_service import MLModelService

        importance = (MLModelService.get_model_metadata().get("feature_importance") or [])[:5]
    except FileNotFoundError:
        importance = []
    for item in importance:
        rows.append([f"Importance {item.get('rank')}: {item.get('feature')}", item.get("importance_mean")])
    notes = [
        "R² is the coefficient of determination on the held-out seasons. It is not classification accuracy.",
        "Feature importance indicates variables that contributed strongly to model predictions. It does not prove causation.",
    ]
    return "SmartCrop model performance", ["Item", "Value"], rows, notes


def _dataset():
    version = DatasetVersion.objects.order_by("-uploaded_at").first()
    if version is None:
        return "SmartCrop dataset report", ["Item", "Value"], [["Datasets", 0]], ["No dataset has been uploaded."]
    quality = {}
    try:
        quality = quality_report(version.file.path)
    except Exception as exc:  # noqa: BLE001
        quality = {"error": str(exc)}
    rows = [
        ["Name", version.dataset.name],
        ["Version", version.version],
        ["Source", version.source],
        ["Source type", version.source_type],
        ["Status", version.status],
        ["Records", version.record_count],
        ["Missing cells", quality.get("missing_cells")],
        ["Duplicate rows", quality.get("duplicate_rows")],
        ["Invalid values", quality.get("invalid_values")],
        ["Feature completeness percent", quality.get("feature_completeness_percent")],
    ]
    notes = [quality.get("completeness_definition") or "Completeness is the share of filled cells."]
    return "SmartCrop dataset report", ["Item", "Value"], rows, notes


def _analytics(user):
    payload = overview_for(user)
    model = payload.get("active_model") or {}
    rows = [
        ["Predictions in view", payload["total_predictions"]],
        ["Average predicted yield (t/ha)", payload["average_predicted_yield"]],
        ["Dataset records", payload["dataset_records"]],
        ["Active model", f"{model.get('algorithm', '')} {model.get('version', '')}".strip()],
        ["Model R²", payload["model_r2"]],
        ["Model RMSE", payload["model_rmse"]],
        ["Model MAE", payload["model_mae"]],
    ]
    for item in (payload.get("feature_importance") or [])[:5]:
        rows.append([f"Importance {item.get('rank')}: {item.get('feature')}", item.get("importance_mean")])
    notes = ["Chart series are omitted from the table. The PDF includes a predictions-by-day chart when predictions exist."]
    return "SmartCrop analytics report", ["Item", "Value"], rows, notes


def _chart(report_type: str, user) -> bytes | None:
    if report_type not in {"analytics", "predictions"}:
        return None
    queryset = Prediction.objects.all()
    if user.role == "farmer" and not user.is_superuser:
        queryset = queryset.filter(user=user)
    if not queryset.exists():
        return None
    from django.db.models import Count
    from django.db.models.functions import TruncDate

    series = list(queryset.annotate(day=TruncDate("created_at")).values("day").annotate(count=Count("id")).order_by("day"))
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar([row["day"].strftime("%m-%d") for row in series], [row["count"] for row in series], color="#1F4D36")
    ax.set_title("Stored predictions by day")
    ax.set_xlabel("Date")
    ax.set_ylabel("Predictions")
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    plt.close(fig)
    return buffer.getvalue()


def _csv(headers, rows) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _xlsx(title, stamp, headers, rows, notes) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Report"
    sheet.append([title])
    sheet.append([stamp])
    sheet.append([])
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    sheet.append([])
    for note in notes:
        sheet.append([note])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _pdf(title, stamp, headers, rows, notes, chart: bytes | None) -> bytes:
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    story = [
        Paragraph("SmartCrop", styles["Title"]),
        Paragraph(title, styles["Heading2"]),
        Paragraph(f"Generated {stamp}. Study area: Macheke, Mashonaland East. Crop: maize.", styles["Normal"]),
        Spacer(1, 0.3 * cm),
        Paragraph(DISCLAIMER, styles["Italic"]),
        Spacer(1, 0.4 * cm),
    ]
    if chart:
        story.append(Image(io.BytesIO(chart), width=16 * cm, height=7 * cm))
        story.append(Spacer(1, 0.3 * cm))
    data = [headers] + [["" if value is None else str(value) for value in row] for row in rows]
    table = Table(data, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EFE4")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#8A8175")),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))
    for note in notes:
        story.append(Paragraph(note, styles["Normal"]))
    SimpleDocTemplate(buffer, pagesize=A4, title=title).build(story)
    return buffer.getvalue()
