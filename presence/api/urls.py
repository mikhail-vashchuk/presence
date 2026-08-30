from django.urls import path

from presence.api.views import (
    AcceptResponseView,
    CancelResponseView,
    CloseInvitationView,
    CompleteMomentView,
    CurrentPresenceView,
    InvitationsView,
    MomentMediaAccessView,
    RejectResponseView,
    SendResponseView,
)


app_name = "presence_api"


urlpatterns = [
    path(
        "invitations/",
        InvitationsView.as_view(),
        name="invitations",
    ),
    path(
        "invitations/<int:invitation_id>/responses/",
        SendResponseView.as_view(),
        name="response-send",
    ),
    path(
        "responses/<int:response_id>/reject/",
        RejectResponseView.as_view(),
        name="response-reject",
    ),
    path(
        "responses/<int:response_id>/accept/",
        AcceptResponseView.as_view(),
        name="response-accept",
    ),
    path(
        "moments/<int:moment_id>/media-access/",
        MomentMediaAccessView.as_view(),
        name="moment-media-access",
    ),
    path(
        "moments/<int:moment_id>/complete/",
        CompleteMomentView.as_view(),
        name="moment-complete",
    ),
    path(
        "invitations/<int:invitation_id>/close/",
        CloseInvitationView.as_view(),
        name="invitation-close",
    ),
    path(
        "responses/<int:response_id>/cancel/",
        CancelResponseView.as_view(),
        name="response-cancel",
    ),
    path(
        "current/",
        CurrentPresenceView.as_view(),
        name="current",
    ),
]
