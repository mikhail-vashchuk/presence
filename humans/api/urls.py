from django.urls import path

from humans.api.views import (
    CompleteRegistrationView,
    StartRegistrationView,
    VerifyRegistrationCodeView,
)


app_name = "humans_api"


urlpatterns = [
    path(
        "registration/start/",
        StartRegistrationView.as_view(),
        name="registration-start",
    ),
    path(
        "registration/<int:verification_id>/verify/",
        VerifyRegistrationCodeView.as_view(),
        name="registration-verify",
    ),
    path(
        "registration/<int:verification_id>/complete/",
        CompleteRegistrationView.as_view(),
        name="registration-complete",
    ),
]