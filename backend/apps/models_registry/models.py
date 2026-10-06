from django.db import models


class ModelVersion(models.Model):
    name = models.CharField(max_length=200, default="smartcrop_maize_yield")
    version = models.CharField(max_length=40, unique=True)
    algorithm = models.CharField(max_length=120)
    target_variable = models.CharField(max_length=80, default="yield_t_ha")
    features = models.JSONField(default=list)
    metrics = models.JSONField(default=dict)
    artifact_path = models.CharField(max_length=500)
    dataset_version = models.CharField(max_length=80, blank=True)
    training_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        state = "active" if self.is_active else "inactive"
        return f"{self.name} {self.version} ({state})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            ModelVersion.objects.exclude(pk=self.pk).update(is_active=False)
