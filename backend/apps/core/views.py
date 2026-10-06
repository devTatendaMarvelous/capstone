from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(summary="Service health", description="Confirms the API process is responding.", auth=[])
    def get(self, request):
        return Response({"status": "ok", "service": "smartcrop"})
