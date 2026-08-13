from django.urls import path

from accounts.api.views import (
    LogoutView,
    StartLoginView,
    VerifyLoginCodeView,
)


app_name = "accounts_api"


urlpatterns = [
    path(
        "login/start/",
        StartLoginView.as_view(),
        name="login-start",
    ),
    path(
        "login/<int:verification_id>/verify/",
        VerifyLoginCodeView.as_view(),
        name="login-verify",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
]