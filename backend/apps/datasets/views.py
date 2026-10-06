from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.audit import write_audit
from apps.core.permissions import IsAtLeast
from apps.core.schema import ErrorResponseSerializer
from apps.datasets.models import Dataset, DatasetVersion
from apps.datasets.quality import quality_report, read_table
from apps.datasets.serializers import DatasetUploadSerializer, DatasetVersionSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List dataset versions",
        parameters=[
            OpenApiParameter(name="search", description="Match name or source.", required=False, type=str),
            OpenApiParameter(name="source_type", description="REAL, SYNTHETIC, or EXTERNAL.", required=False, type=str),
            OpenApiParameter(name="status", required=False, type=str),
        ],
        responses={200: DatasetVersionSerializer(many=True), 401: ErrorResponseSerializer},
    ),
    retrieve=extend_schema(summary="Retrieve one dataset version", responses={200: DatasetVersionSerializer}),
)
class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DatasetVersionSerializer
    permission_classes = [IsAtLeast]
    allowed_roles = ("researcher", "analyst", "farmer", "admin")
    queryset = DatasetVersion.objects.select_related("dataset", "uploaded_by")

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search")
        source_type = self.request.query_params.get("source_type")
        status_value = self.request.query_params.get("status")
        if search:
            queryset = queryset.filter(Q(dataset__name__icontains=search) | Q(source__icontains=search))
        if source_type:
            queryset = queryset.filter(source_type=source_type)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    @extend_schema(
        summary="Upload a dataset version",
        description="Researchers and administrators. CSV or Excel, up to 10 MB. source_type must be REAL, SYNTHETIC, or EXTERNAL.",
        request=DatasetUploadSerializer,
        responses={201: DatasetVersionSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer},
    )
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser], url_path="upload")
    def upload(self, request):
        if request.user.role not in {"researcher", "admin"} and not request.user.is_superuser:
            return Response(
                {"success": False, "message": "You do not have permission to upload datasets.", "errors": {}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DatasetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        dataset, _created = Dataset.objects.get_or_create(
            name=payload["name"],
            defaults={"description": payload.get("description", ""), "created_by": request.user},
        )
        if DatasetVersion.objects.filter(dataset=dataset, version=payload["version"]).exists():
            return Response(
                {
                    "success": False,
                    "message": "That dataset version already exists.",
                    "errors": {"version": ["Choose a new version label."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        version = DatasetVersion(
            dataset=dataset,
            version=payload["version"],
            source=payload["source"],
            source_type=payload["source_type"],
            file=payload["file"],
            uploaded_by=request.user,
            status=DatasetVersion.Status.UPLOADED,
        )
        version.save()
        try:
            frame = read_table(version.file.path)
            version.record_count = int(len(frame))
            version.status = DatasetVersion.Status.VALIDATED
            version.save(update_fields=["record_count", "status"])
        except Exception as exc:  # noqa: BLE001 - store the failure on the version
            version.status = DatasetVersion.Status.FAILED
            version.save(update_fields=["status"])
            write_audit(request.user, "dataset.upload_failed", "dataset_version", version.pk, {"error": str(exc)})
            return Response(
                {"success": False, "message": "The file could not be read as a table.", "errors": {"file": [str(exc)]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        write_audit(request.user, "dataset.upload", "dataset_version", version.pk, {"version": version.version})
        return Response(DatasetVersionSerializer(version).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Dataset quality counts", responses={200: dict, 404: ErrorResponseSerializer})
    @action(detail=True, methods=["get"])
    def quality(self, request, pk=None):
        version = self.get_object()
        report = quality_report(version.file.path)
        return Response(report)
