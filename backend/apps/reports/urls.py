from django.urls import path

from apps.reports.views import AnalyticsReportView, DatasetReportView, ModelReportView, PredictionReportView

urlpatterns = [
    path("predictions/", PredictionReportView.as_view(), name="report-predictions"),
    path("model-performance/", ModelReportView.as_view(), name="report-model"),
    path("dataset/", DatasetReportView.as_view(), name="report-dataset"),
    path("analytics/", AnalyticsReportView.as_view(), name="report-analytics"),
]
