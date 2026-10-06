from django.conf import settings
from django.db import models


class Prediction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions")
    model_version = models.CharField(max_length=40, db_index=True)
    prediction_inputs = models.JSONField()
    predicted_yield = models.FloatField()
    predicted_production = models.FloatField()
    farm_area = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self) -> str:
        return f"{self.predicted_yield:.2f} t/ha by {self.user}"
