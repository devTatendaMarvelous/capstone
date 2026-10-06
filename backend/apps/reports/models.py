from django.conf import settings
from django.db import models


class GeneratedReport(models.Model):
    class ReportType(models.TextChoices):
        PREDICTIONS = "predictions", "Prediction report"
        MODEL = "model-performance", "Model performance report"
        DATASET = "dataset", "Dataset report"
        ANALYTICS = "analytics", "Analytics report"

    report_type = models.CharField(max_length=40, choices=ReportType.choices, db_index=True)
    export_format = models.CharField(max_length=8)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reports")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    row_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.report_type} {self.export_format}"
