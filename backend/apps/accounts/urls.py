from django.urls import path

from apps.accounts.views import MeView, RegisterView, SmartCropRefreshView, SmartCropTokenView, UserListView

urlpatterns = [
    path("token/", SmartCropTokenView.as_view(), name="token"),
    path("token/refresh/", SmartCropRefreshView.as_view(), name="token-refresh"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("users/", UserListView.as_view(), name="users"),
]
