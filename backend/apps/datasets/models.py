from django.conf import settings
from django.db import models


class Dataset(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="datasets")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class DatasetVersion(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        VALIDATED = "validated", "Validated"
        FAILED = "failed", "Failed"

    class SourceType(models.TextChoices):
        REAL = "REAL", "Real"
        SYNTHETIC = "SYNTHETIC", "Synthetic"
        EXTERNAL = "EXTERNAL", "External"

    dataset = models.ForeignKey(Dataset, related_name="versions", on_delete=models.CASCADE)
    version = models.CharField(max_length=40)
    source = models.CharField(max_length=200)
    source_type = models.CharField(max_length=20, choices=SourceType.choices, db_index=True)
    file = models.FileField(upload_to="datasets/%Y/%m/")
    record_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED, db_index=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dataset_uploads")
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(fields=["dataset", "version"], name="unique_dataset_version"),
        ]
        indexes = [models.Index(fields=["source_type", "status"])]

    def __str__(self) -> str:
        return f"{self.dataset.name} {self.version}"
