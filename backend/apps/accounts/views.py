from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import RegisterSerializer, UserSerializer
from apps.core.audit import write_audit
from apps.core.permissions import IsAtLeast
from apps.core.schema import ErrorResponseSerializer

User = get_user_model()


class SmartCropTokenView(TokenObtainPairView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Obtain JWT access and refresh tokens",
        description="Exchange a username and password for a bearer token. The response includes the user's role.",
        auth=[],
        examples=[
            OpenApiExample(
                "Login",
                value={"username": "admin", "password": "replace-me"},
                request_only=True,
            )
        ],
        responses={200: dict, 401: ErrorResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get("username", "")
            user = User.objects.filter(username=username).first()
            if user:
                response.data["user"] = UserSerializer(user).data
                write_audit(user, "auth.login", "user", user.pk)
        return response


class SmartCropRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Refresh a JWT access token", auth=[], responses={200: dict, 401: ErrorResponseSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Register a farmer account",
        description="Public registration creates a farmer. Researcher, analyst, and admin accounts are created by an administrator.",
        auth=[],
        responses={201: UserSerializer, 400: ErrorResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        write_audit(user, "auth.register", "user", user.pk)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Current user", responses={200: UserSerializer, 401: ErrorResponseSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(summary="Update the current user's name", request=UserSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAtLeast]
    allowed_roles = ("admin",)
    queryset = User.objects.order_by("username")

    @extend_schema(summary="List users", description="Administrators only.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
