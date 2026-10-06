"""Aggregates for the dashboard. Every number comes from the database or a stored file."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate

from apps.datasets.models import DatasetVersion
from apps.datasets.quality import quality_report
from apps.models_registry.models import ModelVersion
from apps.predictions.ml_service import MLModelService
from apps.predictions.models import Prediction

User = get_user_model()


def _metadata() -> dict:
    try:
        return MLModelService.get_model_metadata()
    except FileNotFoundError:
        return {}


def _dataset_frame_summary() -> dict:
    version = DatasetVersion.objects.filter(status=DatasetVersion.Status.VALIDATED).order_by("-uploaded_at").first()
    if version is None or not version.file:
        return {"yield_by_season": [], "rainfall_vs_yield": [], "quality": None, "dataset_records": 0}
    try:
        import pandas as pd

        frame = pd.read_csv(version.file.path) if version.file.path.endswith(".csv") else __import__("pandas").read_excel(version.file.path)
    except Exception:
        return {"yield_by_season": [], "rainfall_vs_yield": [], "quality": None, "dataset_records": version.record_count}
    season = []
    if {"season", "yield_t_ha"}.issubset(frame.columns):
        grouped = frame.dropna(subset=["yield_t_ha"]).groupby("season")["yield_t_ha"].mean()
        season = [{"season": str(key), "mean_yield_t_ha": round(float(value), 3)} for key, value in grouped.items()]
    rainfall = []
    if {"rainfall_mm", "yield_t_ha"}.issubset(frame.columns):
        sample = frame.dropna(subset=["rainfall_mm", "yield_t_ha"]).head(250)
        rainfall = [
            {"rainfall_mm": round(float(row.rainfall_mm), 1), "yield_t_ha": round(float(row.yield_t_ha), 3)}
            for row in sample.itertuples(index=False)
        ]
    quality = None
    try:
        quality = quality_report(version.file.path)
    except Exception:
        quality = None
    return {
        "yield_by_season": season,
        "rainfall_vs_yield": rainfall,
        "quality": quality,
        "dataset_records": int(version.record_count),
    }


def _bins(values: list[float]) -> list[dict]:
    if not values:
        return []
    low, high = min(values), max(values)
    if low == high:
        return [{"label": f"{low:.1f}", "count": len(values)}]
    width = (high - low) / 6
    counts = [0] * 6
    for value in values:
        index = min(5, int((value - low) / width))
        counts[index] += 1
    return [
        {"label": f"{low + index * width:.1f}–{low + (index + 1) * width:.1f}", "count": count}
        for index, count in enumerate(counts)
    ]


def overview_for(user) -> dict:
    privileged = user.is_superuser or user.role in {"admin", "researcher", "analyst"}
    mine = Prediction.objects.filter(user=user)
    population = Prediction.objects.all() if privileged else mine
    metadata = _metadata()
    active = ModelVersion.objects.filter(is_active=True).first()
    metrics = (active.metrics if active else None) or metadata.get("metrics") or {}
    average = population.aggregate(value=Avg("predicted_yield"))["value"]
    by_day = (
        population.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    yields = list(population.values_list("predicted_yield", flat=True))
    dataset = _dataset_frame_summary()
    importance = metadata.get("feature_importance") or []
    return {
        "total_predictions": population.count(),
        "my_predictions": mine.count(),
        "average_predicted_yield": round(float(average), 3) if average is not None else None,
        "active_model": None
        if active is None
        else {
            "name": active.name,
            "version": active.version,
            "algorithm": active.algorithm,
            "r2": metrics.get("r2"),
            "rmse": metrics.get("rmse"),
            "mae": metrics.get("mae"),
        },
        "model_r2": metrics.get("r2"),
        "model_rmse": metrics.get("rmse"),
        "model_mae": metrics.get("mae"),
        "dataset_records": dataset["dataset_records"],
        "total_datasets": DatasetVersion.objects.count() if privileged else None,
        "total_users": User.objects.count() if privileged else None,
        "predictions_over_time": [
            {"date": row["day"].isoformat() if row["day"] else None, "count": row["count"]} for row in by_day
        ],
        "yield_distribution": _bins([float(value) for value in yields]),
        "feature_importance": importance[:9],
        "yield_by_season": dataset["yield_by_season"],
        "rainfall_vs_yield": dataset["rainfall_vs_yield"],
        "data_quality": dataset["quality"],
        "recent_predictions": [
            {
                "id": item.id,
                "predicted_yield": item.predicted_yield,
                "predicted_production": item.predicted_production,
                "farm_area": item.farm_area,
                "model_version": item.model_version,
                "created_at": item.created_at.isoformat(),
                "username": item.user.username,
            }
            for item in population.select_related("user")[:8]
        ],
        "disclaimer": metadata.get("disclaimer", ""),
    }


def admin_dashboard() -> dict:
    active = ModelVersion.objects.filter(is_active=True).first()
    metrics = (active.metrics if active else {}) or {}
    population = Prediction.objects.all()
    average = population.aggregate(value=Avg("predicted_yield"))["value"]
    by_day = list(
        population.annotate(day=TruncDate("created_at")).values("day").annotate(count=Count("id")).order_by("day")
    )
    peak = max((row["count"] for row in by_day), default=1) or 1
    bars = []
    for index, row in enumerate(by_day[-10:]):
        height = 110 * row["count"] / peak
        bars.append(
            {
                "x": 8 + index * 46,
                "y": 130 - height,
                "width": 28,
                "height": max(height, 0),
                "label": row["day"].strftime("%m-%d") if row["day"] else "",
            }
        )
    return {
        "users": User.objects.count(),
        "datasets": DatasetVersion.objects.count(),
        "predictions": population.count(),
        "active_label": f"{active.algorithm} {active.version}" if active else "No active model",
        "r2": metrics.get("r2", "—"),
        "rmse": metrics.get("rmse", "—"),
        "mae": metrics.get("mae", "—"),
        "average_yield": round(float(average), 3) if average is not None else "—",
        "bars": bars,
    }
