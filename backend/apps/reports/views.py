from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.core.audit import write_audit
from apps.core.permissions import IsAtLeast
from apps.core.schema import ErrorResponseSerializer
from apps.reports.models import GeneratedReport
from apps.reports.services import render_report

FORMAT_PARAMETER = OpenApiParameter(
    name="format",
    description="pdf, xlsx, or csv. Defaults to pdf.",
    required=False,
    type=str,
)


class ReportView(APIView):
    permission_classes = [IsAtLeast]
    allowed_roles = ("farmer", "analyst", "researcher", "admin")
    report_type = ""
    summary = ""
    description = ""

    def perform_content_negotiation(self, request, force=False):
        # `format` selects pdf, xlsx, or csv. DRF otherwise treats it as a renderer suffix and 404s.
        renderer = self.get_renderers()[0]
        return (renderer, renderer.media_type)

    @extend_schema(
        summary="Download a report",
        parameters=[FORMAT_PARAMETER],
        responses={200: bytes, 400: ErrorResponseSerializer},
    )
    def get(self, request):
        export_format = request.query_params.get("format", "pdf").lower()
        if export_format not in {"pdf", "xlsx", "csv"}:
            return HttpResponse(
                '{"success": false, "message": "Unsupported report format.", "errors": {"format": ["Use pdf, xlsx, or csv."]}}',
                status=400,
                content_type="application/json",
            )
        body, media, filename = render_report(self.report_type, export_format, request.user)
        GeneratedReport.objects.create(
            report_type=self.report_type,
            export_format=export_format,
            created_by=request.user,
            row_count=body.count(b"\n") if export_format == "csv" else 0,
        )
        write_audit(request.user, "report.download", "report", self.report_type, {"format": export_format})
        response = HttpResponse(body, content_type=media)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class PredictionReportView(ReportView):
    report_type = "predictions"
    summary = "Prediction report"

    @extend_schema(summary="Download the prediction report", parameters=[FORMAT_PARAMETER])
    def get(self, request):
        return super().get(request)


class ModelReportView(ReportView):
    report_type = "model-performance"

    @extend_schema(summary="Download the model performance report", parameters=[FORMAT_PARAMETER])
    def get(self, request):
        return super().get(request)


class DatasetReportView(ReportView):
    report_type = "dataset"

    @extend_schema(summary="Download the dataset report", parameters=[FORMAT_PARAMETER])
    def get(self, request):
        return super().get(request)


class AnalyticsReportView(ReportView):
    report_type = "analytics"

    @extend_schema(summary="Download the analytics report", parameters=[FORMAT_PARAMETER])
    def get(self, request):
        return super().get(request)
