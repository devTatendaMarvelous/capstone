from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.services import overview_for
from apps.core.permissions import IsAtLeast
from apps.core.schema import ErrorResponseSerializer


class OverviewView(APIView):
    permission_classes = [IsAtLeast]
    allowed_roles = ("farmer", "analyst", "researcher", "admin")

    @extend_schema(
        summary="Dashboard analytics",
        description=(
            "Counts, model metrics, and chart series computed from stored predictions, "
            "the active model, and the latest validated dataset file. Empty lists mean "
            "there is no data yet. Nothing on this endpoint is hard-coded."
        ),
        responses={200: dict, 401: ErrorResponseSerializer},
    )
    def get(self, request):
        return Response(overview_for(request.user))
